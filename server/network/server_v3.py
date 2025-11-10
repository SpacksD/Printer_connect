"""
Servidor TCP/IP con integración de BD y cola (Fase 3)
"""

import socket
import threading
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional
import uuid
import sys

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import Protocol, Message
from shared.constants import MESSAGE_TYPE_PRINT_JOB, BUFFER_SIZE
from server.network.protocol import (
    parse_print_job,
    create_success_response,
    create_error_response
)
from server.database.database import Database
from server.database.models import PrintJob
from server.printer.printer_manager import PrinterManager
from server.printer.job_processor import JobProcessor


class PrintServerV3:
    """Servidor TCP/IP con integración de BD y cola de impresión"""

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 9100,
        temp_folder: Path = Path('./temp'),
        database: Optional[Database] = None,
        job_processor: Optional[JobProcessor] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el servidor

        Args:
            host: Dirección IP para escuchar
            port: Puerto para escuchar
            temp_folder: Carpeta temporal para guardar archivos recibidos
            database: Instancia de base de datos
            job_processor: Procesador de trabajos
            logger: Logger para mensajes
        """
        self.host = host
        self.port = port
        self.temp_folder = Path(temp_folder)
        self.logger = logger or logging.getLogger(__name__)
        self.running = False
        self.server_socket: Optional[socket.socket] = None

        # Crear carpeta temporal si no existe
        self.temp_folder.mkdir(parents=True, exist_ok=True)

        # Base de datos
        self.database = database

        # Procesador de trabajos
        self.job_processor = job_processor

        self.logger.info(
            f"Servidor V3 inicializado en {host}:{port} "
            f"(BD={'Sí' if database else 'No'}, "
            f"Cola={'Sí' if job_processor else 'No'})"
        )

    def start(self):
        """Inicia el servidor"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            self.logger.info(f"Servidor V3 escuchando en {self.host}:{self.port}")

            # Iniciar procesador de trabajos si está disponible
            if self.job_processor:
                self.job_processor.start()

            while self.running:
                try:
                    # Aceptar conexión
                    client_socket, address = self.server_socket.accept()
                    self.logger.info(f"Conexión entrante desde {address}")

                    # Manejar cliente en un thread separado
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error aceptando conexión: {e}")

        except Exception as e:
            self.logger.error(f"Error iniciando servidor: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Detiene el servidor"""
        self.logger.info("Deteniendo servidor...")
        self.running = False

        # Detener procesador de trabajos
        if self.job_processor:
            self.job_processor.stop()

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                self.logger.error(f"Error cerrando socket: {e}")

        self.logger.info("Servidor detenido")

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """
        Maneja una conexión de cliente

        Args:
            client_socket: Socket del cliente
            address: Dirección del cliente
        """
        try:
            # Recibir mensaje completo
            data = Protocol.receive_full_message(client_socket, BUFFER_SIZE)

            if not data:
                self.logger.warning(f"Conexión cerrada por {address}")
                return

            # Decodificar mensaje
            message = Protocol.decode_message(data)
            self.logger.info(f"Mensaje recibido de {address}: {message}")

            # Procesar mensaje según tipo
            if message.message_type == MESSAGE_TYPE_PRINT_JOB:
                response = self._handle_print_job(message, address)
            else:
                response = create_error_response(
                    f"Tipo de mensaje no soportado: {message.message_type}",
                    error_code='UNSUPPORTED_MESSAGE_TYPE'
                )

            # Enviar respuesta
            response_data = Protocol.encode_message(response)
            client_socket.sendall(response_data)
            self.logger.info(f"Respuesta enviada a {address}")

        except Exception as e:
            self.logger.error(f"Error manejando cliente {address}: {e}", exc_info=True)

            try:
                # Intentar enviar respuesta de error
                error_response = create_error_response(
                    f"Error del servidor: {str(e)}",
                    error_code='SERVER_ERROR'
                )
                response_data = Protocol.encode_message(error_response)
                client_socket.sendall(response_data)
            except Exception as send_error:
                self.logger.error(f"Error enviando respuesta de error: {send_error}")

        finally:
            try:
                client_socket.close()
            except Exception as e:
                self.logger.error(f"Error cerrando socket del cliente: {e}")

    def _handle_print_job(self, message: Message, address: tuple) -> Message:
        """
        Maneja un trabajo de impresión

        Args:
            message: Mensaje con el trabajo de impresión
            address: Dirección del cliente

        Returns:
            Mensaje de respuesta
        """
        try:
            # Parsear trabajo de impresión
            job_data = parse_print_job(message)

            # Generar ID único para el trabajo
            job_id = f"JOB-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

            self.logger.info(
                f"Trabajo de impresión recibido: {job_id} de {job_data['user']} "
                f"({job_data['metadata'].document_name})"
            )

            # Guardar archivo en carpeta temporal
            file_extension = job_data['file_format']
            temp_file = self.temp_folder / f"{job_id}.{file_extension}"

            with open(temp_file, 'wb') as f:
                f.write(job_data['file_content'])

            self.logger.info(f"Archivo guardado: {temp_file}")

            # Si tenemos BD, guardar el trabajo
            if self.database:
                self.logger.debug("Guardando trabajo en base de datos...")

                # Actualizar o crear cliente
                self.database.create_or_update_client(
                    client_id=job_data['client_id'],
                    ip_address=address[0]
                )

                # Preparar datos del trabajo
                params = job_data['parameters']
                metadata = job_data['metadata']

                print_job_data = {
                    'job_id': job_id,
                    'client_id': job_data['client_id'],
                    'user_name': job_data['user'],
                    'document_name': metadata.document_name,
                    'file_format': job_data['file_format'],
                    'file_size_bytes': len(job_data['file_content']),
                    'file_path': str(temp_file),
                    'page_size': params.page_size.value,
                    'orientation': params.orientation.value,
                    'copies': params.copies,
                    'color': params.color,
                    'duplex': params.duplex,
                    'quality': params.quality,
                    'margin_top': params.margins.top,
                    'margin_bottom': params.margins.bottom,
                    'margin_left': params.margins.left,
                    'margin_right': params.margins.right,
                    'page_count': metadata.page_count,
                    'application': metadata.application,
                    'status': 'pending',
                    'priority': 5,  # Prioridad por defecto
                }

                # Crear registro en BD
                db_job = self.database.create_print_job(print_job_data)
                self.logger.info(f"Trabajo guardado en BD con ID: {db_job.id}")

                # Si tenemos procesador, enviar a cola
                if self.job_processor:
                    self.logger.debug("Enviando trabajo a cola de impresión...")
                    self.job_processor.submit_job(db_job)

                # Obtener posición en cola
                queue_position = self.job_processor.queue_manager.get_queue_size() if self.job_processor else 1

            else:
                # Sin BD, solo guardamos archivo (como en Fase 1)
                self.logger.warning("Sin BD, solo guardando archivo")
                queue_position = 1

            # Log de parámetros
            self.logger.debug(f"Parámetros: {job_data['parameters'].to_dict()}")
            self.logger.debug(f"Metadatos: {job_data['metadata'].to_dict()}")

            # Crear respuesta exitosa
            return create_success_response(
                message=f"Trabajo de impresión recibido y procesado: {job_id}",
                job_id=job_id,
                queue_position=queue_position
            )

        except Exception as e:
            self.logger.error(f"Error procesando trabajo de impresión: {e}", exc_info=True)
            return create_error_response(
                f"Error procesando trabajo de impresión: {str(e)}",
                error_code='PRINT_JOB_ERROR'
            )


def main():
    """Función principal para ejecutar el servidor V3"""
    import sys

    # Setup básico de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Crear base de datos
    database = Database(
        db_url="sqlite:///./data/printer_connect.db",
        logger=logger
    )

    # Crear gestor de impresora (mock para pruebas)
    printer_manager = PrinterManager(
        use_mock=True,
        logger=logger
    )

    # Crear procesador de trabajos
    job_processor = JobProcessor(
        database=database,
        printer_manager=printer_manager,
        logger=logger
    )

    # Crear y arrancar servidor
    server = PrintServerV3(
        host='0.0.0.0',
        port=9100,
        database=database,
        job_processor=job_processor,
        logger=logger
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nInterrumpido por usuario")
        server.stop()


if __name__ == '__main__':
    main()
