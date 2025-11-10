"""
Servidor TCP/IP para recepción de trabajos de impresión
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


class PrintServer:
    """Servidor TCP/IP que recibe trabajos de impresión"""

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 9100,
        temp_folder: Path = Path('./temp'),
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el servidor

        Args:
            host: Dirección IP para escuchar
            port: Puerto para escuchar
            temp_folder: Carpeta temporal para guardar archivos recibidos
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

        self.logger.info(f"Servidor inicializado en {host}:{port}")

    def start(self):
        """Inicia el servidor"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            self.logger.info(f"Servidor escuchando en {self.host}:{self.port}")

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

            # Log de parámetros
            self.logger.debug(f"Parámetros: {job_data['parameters'].to_dict()}")
            self.logger.debug(f"Metadatos: {job_data['metadata'].to_dict()}")

            # TODO: En futuras fases, aquí se enviará a la cola de impresión

            # Crear respuesta exitosa
            return create_success_response(
                message=f"Trabajo de impresión recibido y procesado: {job_id}",
                job_id=job_id,
                queue_position=1
            )

        except Exception as e:
            self.logger.error(f"Error procesando trabajo de impresión: {e}", exc_info=True)
            return create_error_response(
                f"Error procesando trabajo de impresión: {str(e)}",
                error_code='PRINT_JOB_ERROR'
            )


def main():
    """Función principal para ejecutar el servidor"""
    # Setup básico de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Crear y arrancar servidor
    server = PrintServer(host='0.0.0.0', port=9100)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nInterrumpido por usuario")
        server.stop()


if __name__ == '__main__':
    main()
