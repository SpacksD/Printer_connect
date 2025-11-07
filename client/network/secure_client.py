"""
Cliente TCP/IP con TLS y autenticación JWT (Fase 4)
Versión segura del cliente de impresión
"""

import sys
import socket
import ssl
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import Protocol, Message
from shared.data_models import PrintJob, PrintParameters, PrintJobMetadata, ServerResponse
from shared.security.tls_wrapper import TLSSocketWrapper, create_client_context
from shared.security.auth import AuthenticationManager


class SecurePrintClient:
    """
    Cliente de impresión seguro con TLS y autenticación JWT
    """

    def __init__(
        self,
        server_host: str,
        server_port: int,
        client_id: str,
        auth_token: Optional[str] = None,
        certfile: Optional[Path] = None,
        keyfile: Optional[Path] = None,
        cafile: Optional[Path] = None,
        verify_server: bool = True,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el cliente seguro

        Args:
            server_host: Dirección del servidor
            server_port: Puerto del servidor
            client_id: ID único del cliente
            auth_token: Token JWT de autenticación (si ya se tiene)
            certfile: Certificado del cliente (para autenticación mutua)
            keyfile: Clave privada del cliente (para autenticación mutua)
            cafile: CA para verificar servidor
            verify_server: Verificar certificado del servidor
            timeout: Timeout de conexión en segundos
            logger: Logger para mensajes
        """
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.auth_token = auth_token
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        # Configuración TLS
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile
        self.verify_server = verify_server

        # Crear contexto TLS
        self.tls_context = create_client_context(
            certfile=certfile,
            keyfile=keyfile,
            cafile=cafile,
            verify_server=verify_server,
            logger=self.logger
        )

        self.logger.info(
            f"SecurePrintClient inicializado "
            f"(server={server_host}:{server_port}, client_id={client_id})"
        )

    def set_auth_token(self, token: str):
        """
        Establece el token de autenticación

        Args:
            token: Token JWT
        """
        self.auth_token = token
        self.logger.info("Token de autenticación actualizado")

    def _create_connection(self) -> TLSSocketWrapper:
        """
        Crea una conexión TLS con el servidor

        Returns:
            Socket TLS conectado

        Raises:
            ConnectionError: Si no se puede conectar
        """
        try:
            # Crear socket TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            # Conectar al servidor
            self.logger.debug(f"Conectando a {self.server_host}:{self.server_port}")
            sock.connect((self.server_host, self.server_port))

            # Envolver con TLS
            tls_socket = TLSSocketWrapper(
                sock=sock,
                context=self.tls_context,
                server_side=False,
                server_hostname=self.server_host,
                logger=self.logger
            )

            self.logger.debug("Conexión TLS establecida")

            # Log información del cifrado
            cipher = tls_socket.get_cipher()
            if cipher:
                self.logger.info(f"Cifrado: {cipher[0]} ({cipher[1]})")

            return tls_socket

        except socket.timeout:
            raise ConnectionError(f"Timeout conectando a {self.server_host}:{self.server_port}")

        except ssl.SSLError as e:
            raise ConnectionError(f"Error TLS: {e}")

        except Exception as e:
            raise ConnectionError(f"Error de conexión: {e}")

    def _send_message(
        self,
        tls_socket: TLSSocketWrapper,
        message: Message
    ):
        """
        Envía un mensaje al servidor

        Args:
            tls_socket: Socket TLS
            message: Mensaje a enviar
        """
        # Agregar token de autenticación a headers
        if self.auth_token:
            message.headers['Authorization'] = f'Bearer {self.auth_token}'
        else:
            self.logger.warning("No hay token de autenticación configurado")

        # Codificar y enviar
        message_bytes = Protocol.encode_message(message)
        tls_socket.sendall(message_bytes)

    def _receive_response(self, tls_socket: TLSSocketWrapper) -> ServerResponse:
        """
        Recibe una respuesta del servidor

        Args:
            tls_socket: Socket TLS

        Returns:
            ServerResponse recibida
        """
        response_bytes = Protocol.receive_full_message(tls_socket)

        if not response_bytes:
            raise ConnectionError("Servidor cerró la conexión")

        # Decodificar mensaje
        message = Protocol.decode_message(response_bytes)

        # Convertir a ServerResponse
        return ServerResponse.from_dict(message.body)

    def send_print_job(
        self,
        user: str,
        file_path: Path,
        parameters: Optional[PrintParameters] = None,
        metadata: Optional[PrintJobMetadata] = None
    ) -> Dict[str, Any]:
        """
        Envía un trabajo de impresión al servidor

        Args:
            user: Usuario que solicita la impresión
            file_path: Ruta al archivo a imprimir
            parameters: Parámetros de impresión
            metadata: Metadata del trabajo

        Returns:
            Dictionary con la respuesta del servidor

        Raises:
            ConnectionError: Si hay error de conexión
            ValueError: Si el archivo no existe
        """
        if not file_path.exists():
            raise ValueError(f"Archivo no encontrado: {file_path}")

        if not self.auth_token:
            raise ValueError("Token de autenticación no configurado")

        self.logger.info(f"Enviando trabajo de impresión: {file_path}")

        try:
            # Leer archivo
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Crear PrintJob
            print_job = PrintJob(
                client_id=self.client_id,
                user=user,
                file_path=str(file_path),
                parameters=parameters or PrintParameters(),
                metadata=metadata or PrintJobMetadata(
                    document_name=file_path.name,
                    file_size_bytes=len(file_data)
                )
            )

            # Crear mensaje
            message = Message(
                type='print_job',
                body=print_job.to_dict(),
                file_data=file_data
            )

            # Conectar y enviar
            with self._create_connection() as tls_socket:
                self._send_message(tls_socket, message)

                # Recibir respuesta
                response = self._receive_response(tls_socket)

            if response.status == 'success':
                self.logger.info(f"✓ Trabajo enviado: {response.data.get('job_id')}")
            else:
                self.logger.error(f"✗ Error del servidor: {response.message}")

            return response.to_dict()

        except ConnectionError:
            raise

        except Exception as e:
            self.logger.error(f"Error enviando trabajo: {e}", exc_info=True)
            raise ConnectionError(f"Error enviando trabajo: {e}")

    def ping(self) -> Dict[str, Any]:
        """
        Envía un ping al servidor

        Returns:
            Dictionary con la respuesta

        Raises:
            ConnectionError: Si hay error de conexión
        """
        if not self.auth_token:
            raise ValueError("Token de autenticación no configurado")

        try:
            message = Message(type='ping', body={})

            with self._create_connection() as tls_socket:
                self._send_message(tls_socket, message)
                response = self._receive_response(tls_socket)

            return response.to_dict()

        except Exception as e:
            raise ConnectionError(f"Error en ping: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado del servidor

        Returns:
            Dictionary con estadísticas del servidor

        Raises:
            ConnectionError: Si hay error de conexión
        """
        if not self.auth_token:
            raise ValueError("Token de autenticación no configurado")

        try:
            message = Message(type='status', body={})

            with self._create_connection() as tls_socket:
                self._send_message(tls_socket, message)
                response = self._receive_response(tls_socket)

            return response.to_dict()

        except Exception as e:
            raise ConnectionError(f"Error obteniendo estado: {e}")

    def test_connection(self) -> bool:
        """
        Prueba la conexión con el servidor

        Returns:
            True si se puede conectar, False si no
        """
        try:
            result = self.ping()
            return result.get('status') == 'success'

        except Exception as e:
            self.logger.error(f"Error probando conexión: {e}")
            return False


class ClientAuthenticator:
    """
    Ayuda a los clientes a autenticarse y obtener tokens
    """

    def __init__(
        self,
        server_host: str,
        server_port: int,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el autenticador

        Args:
            server_host: Dirección del servidor de autenticación
            server_port: Puerto del servidor
            logger: Logger para mensajes
        """
        self.server_host = server_host
        self.server_port = server_port
        self.logger = logger or logging.getLogger(__name__)

    def authenticate(
        self,
        client_id: str,
        username: str,
        password: str
    ) -> Optional[str]:
        """
        Autentica un cliente y obtiene un token JWT

        Args:
            client_id: ID del cliente
            username: Nombre de usuario
            password: Contraseña

        Returns:
            Token JWT o None si falla

        Note:
            Esta es una implementación simplificada.
            En producción, esto debería ser un endpoint REST separado.
        """
        # TODO: Implementar endpoint de autenticación en el servidor
        # Por ahora, esta función es un placeholder

        self.logger.warning(
            "authenticate() es un placeholder. "
            "Implementar endpoint de autenticación en el servidor."
        )

        return None

    def refresh_token(self, old_token: str) -> Optional[str]:
        """
        Renueva un token existente

        Args:
            old_token: Token a renovar

        Returns:
            Nuevo token o None si falla
        """
        # TODO: Implementar endpoint de refresh en el servidor
        self.logger.warning(
            "refresh_token() es un placeholder. "
            "Implementar endpoint de refresh en el servidor."
        )

        return None
