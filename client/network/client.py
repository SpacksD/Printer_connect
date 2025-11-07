"""
Cliente TCP/IP para envío de trabajos de impresión
"""

import socket
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import sys

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import Protocol, Message
from shared.constants import BUFFER_SIZE, CONNECTION_TIMEOUT
from shared.data_models import PrintParameters, PrintJobMetadata
from client.network.protocol import create_print_request


class PrintClient:
    """Cliente TCP/IP para envío de trabajos de impresión"""

    def __init__(
        self,
        server_host: str,
        server_port: int = 9100,
        timeout: int = CONNECTION_TIMEOUT,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el cliente

        Args:
            server_host: Dirección IP del servidor
            server_port: Puerto del servidor
            timeout: Timeout de conexión en segundos
            logger: Logger para mensajes
        """
        self.server_host = server_host
        self.server_port = server_port
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info(f"Cliente configurado para {server_host}:{server_port}")

    def send_print_job(
        self,
        client_id: str,
        user: str,
        file_path: Path,
        parameters: PrintParameters,
        metadata: PrintJobMetadata
    ) -> Dict[str, Any]:
        """
        Envía un trabajo de impresión al servidor

        Args:
            client_id: ID del cliente
            user: Usuario que solicita la impresión
            file_path: Ruta al archivo a imprimir
            parameters: Parámetros de impresión
            metadata: Metadatos del documento

        Returns:
            Diccionario con la respuesta del servidor

        Raises:
            ConnectionError: Si no se puede conectar al servidor
            Exception: Si ocurre un error durante el envío
        """
        client_socket = None

        try:
            # Crear mensaje de trabajo de impresión
            self.logger.info(f"Preparando trabajo de impresión: {file_path}")
            message = create_print_request(
                client_id=client_id,
                user=user,
                file_path=file_path,
                parameters=parameters,
                metadata=metadata
            )

            # Conectar al servidor
            self.logger.info(f"Conectando a {self.server_host}:{self.server_port}...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.timeout)
            client_socket.connect((self.server_host, self.server_port))
            self.logger.info("Conectado exitosamente")

            # Codificar y enviar mensaje
            self.logger.info("Enviando trabajo de impresión...")
            encoded_message = Protocol.encode_message(message)
            client_socket.sendall(encoded_message)
            self.logger.info(f"Enviados {len(encoded_message)} bytes")

            # Recibir respuesta
            self.logger.info("Esperando respuesta del servidor...")
            response_data = Protocol.receive_full_message(client_socket, BUFFER_SIZE)

            if not response_data:
                raise ConnectionError("El servidor cerró la conexión sin responder")

            # Decodificar respuesta
            response = Protocol.decode_message(response_data)
            self.logger.info(f"Respuesta recibida: {response}")

            # Parsear respuesta
            response_dict = response.data

            if response_dict['status'] == 'success':
                self.logger.info(
                    f"Trabajo enviado exitosamente. Job ID: {response_dict.get('job_id')}"
                )
            else:
                self.logger.error(
                    f"Error del servidor: {response_dict.get('message')} "
                    f"({response_dict.get('error_code')})"
                )

            return response_dict

        except socket.timeout:
            self.logger.error("Timeout conectando al servidor")
            raise ConnectionError("Timeout conectando al servidor")

        except socket.error as e:
            self.logger.error(f"Error de socket: {e}")
            raise ConnectionError(f"Error de red: {e}")

        except Exception as e:
            self.logger.error(f"Error enviando trabajo de impresión: {e}", exc_info=True)
            raise

        finally:
            if client_socket:
                try:
                    client_socket.close()
                    self.logger.debug("Socket cerrado")
                except Exception as e:
                    self.logger.error(f"Error cerrando socket: {e}")

    def test_connection(self) -> bool:
        """
        Prueba la conexión con el servidor

        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            self.logger.info(f"Probando conexión a {self.server_host}:{self.server_port}...")
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(5)
            test_socket.connect((self.server_host, self.server_port))
            test_socket.close()
            self.logger.info("Conexión exitosa")
            return True
        except Exception as e:
            self.logger.error(f"Error probando conexión: {e}")
            return False


def main():
    """Función principal para prueba del cliente"""
    import os
    import platform

    # Setup básico de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Crear cliente
    client = PrintClient(server_host='127.0.0.1', server_port=9100)

    # Probar conexión
    if not client.test_connection():
        print("No se pudo conectar al servidor. Asegúrate de que esté corriendo.")
        return

    # Crear un archivo PDF de prueba (vacío)
    test_file = Path('./test_document.pdf')
    if not test_file.exists():
        with open(test_file, 'wb') as f:
            f.write(b'%PDF-1.4\nTest PDF\n%%EOF')
        print(f"Archivo de prueba creado: {test_file}")

    # Preparar parámetros de impresión
    parameters = PrintParameters()
    metadata = PrintJobMetadata(
        document_name="test_document.pdf",
        page_count=1,
        application="PrintClient Test",
        file_size_bytes=test_file.stat().st_size
    )

    # Enviar trabajo de impresión
    try:
        client_id = "TEST-CLIENT-001"
        user = os.getenv('USER', os.getenv('USERNAME', 'test_user'))

        print(f"\nEnviando trabajo de impresión...")
        print(f"Cliente: {client_id}")
        print(f"Usuario: {user}")
        print(f"Archivo: {test_file}")

        response = client.send_print_job(
            client_id=client_id,
            user=user,
            file_path=test_file,
            parameters=parameters,
            metadata=metadata
        )

        print(f"\n=== Respuesta del servidor ===")
        print(f"Estado: {response['status']}")
        print(f"Mensaje: {response['message']}")
        if response.get('job_id'):
            print(f"Job ID: {response['job_id']}")
        if response.get('queue_position'):
            print(f"Posición en cola: {response['queue_position']}")

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == '__main__':
    main()
