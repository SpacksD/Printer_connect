"""
Wrapper para conexiones TLS/SSL
Simplifica el uso de sockets seguros en cliente y servidor
"""

import ssl
import socket
import logging
from pathlib import Path
from typing import Optional, Union


class TLSSocketWrapper:
    """Wrapper para sockets con TLS/SSL"""

    def __init__(
        self,
        sock: socket.socket,
        context: ssl.SSLContext,
        server_side: bool = False,
        server_hostname: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el wrapper TLS

        Args:
            sock: Socket a envolver
            context: Contexto SSL
            server_side: True si es lado servidor
            server_hostname: Hostname del servidor (para verificación del cliente)
            logger: Logger para mensajes
        """
        self.logger = logger or logging.getLogger(__name__)
        self.server_side = server_side

        # Envolver socket con TLS
        try:
            if server_side:
                self.ssl_sock = context.wrap_socket(
                    sock,
                    server_side=True
                )
            else:
                self.ssl_sock = context.wrap_socket(
                    sock,
                    server_side=False,
                    server_hostname=server_hostname
                )

            self.logger.debug(
                f"Socket TLS creado (server_side={server_side}, "
                f"hostname={server_hostname})"
            )

        except ssl.SSLError as e:
            self.logger.error(f"Error creando socket TLS: {e}")
            raise

    def send(self, data: bytes) -> int:
        """Envía datos por el socket TLS"""
        return self.ssl_sock.send(data)

    def sendall(self, data: bytes):
        """Envía todos los datos por el socket TLS"""
        self.ssl_sock.sendall(data)

    def recv(self, bufsize: int) -> bytes:
        """Recibe datos del socket TLS"""
        return self.ssl_sock.recv(bufsize)

    def close(self):
        """Cierra el socket TLS"""
        try:
            self.ssl_sock.close()
        except Exception as e:
            self.logger.warning(f"Error cerrando socket TLS: {e}")

    def getpeername(self):
        """Obtiene información del peer"""
        return self.ssl_sock.getpeername()

    def get_peer_cert(self) -> Optional[dict]:
        """Obtiene el certificado del peer"""
        try:
            return self.ssl_sock.getpeercert()
        except Exception:
            return None

    def get_cipher(self) -> Optional[tuple]:
        """Obtiene información del cifrado usado"""
        try:
            return self.ssl_sock.cipher()
        except Exception:
            return None

    def __enter__(self):
        """Contexto manager: entrada"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Contexto manager: salida"""
        self.close()


def create_tls_context(
    purpose: ssl.Purpose,
    certfile: Optional[Path] = None,
    keyfile: Optional[Path] = None,
    cafile: Optional[Path] = None,
    verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED,
    check_hostname: bool = True,
    logger: Optional[logging.Logger] = None
) -> ssl.SSLContext:
    """
    Crea un contexto SSL/TLS configurado

    Args:
        purpose: Propósito del contexto (CLIENT_AUTH o SERVER_AUTH)
        certfile: Ruta al archivo de certificado
        keyfile: Ruta al archivo de clave privada
        cafile: Ruta al archivo CA para verificación
        verify_mode: Modo de verificación (CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE)
        check_hostname: Verificar hostname del certificado
        logger: Logger para mensajes

    Returns:
        Contexto SSL configurado

    Raises:
        FileNotFoundError: Si algún archivo no existe
        ssl.SSLError: Si hay error configurando TLS
    """
    logger = logger or logging.getLogger(__name__)

    # Crear contexto base
    context = ssl.create_default_context(purpose=purpose)

    # Configurar protocolo y opciones
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Opciones de seguridad
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1

    # Configurar verificación
    context.verify_mode = verify_mode
    context.check_hostname = check_hostname

    # Cargar certificado y clave (para servidor o autenticación mutua)
    if certfile and keyfile:
        if not certfile.exists():
            raise FileNotFoundError(f"Certificado no encontrado: {certfile}")
        if not keyfile.exists():
            raise FileNotFoundError(f"Clave privada no encontrada: {keyfile}")

        logger.info(f"Cargando certificado: {certfile}")
        context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))

    # Cargar CA para verificación (para cliente)
    if cafile:
        if not cafile.exists():
            raise FileNotFoundError(f"Archivo CA no encontrado: {cafile}")

        logger.info(f"Cargando CA: {cafile}")
        context.load_verify_locations(cafile=str(cafile))

    logger.info(
        f"Contexto TLS creado (purpose={purpose}, verify_mode={verify_mode}, "
        f"check_hostname={check_hostname})"
    )

    return context


def create_server_context(
    certfile: Path,
    keyfile: Path,
    cafile: Optional[Path] = None,
    require_client_cert: bool = False,
    logger: Optional[logging.Logger] = None
) -> ssl.SSLContext:
    """
    Crea un contexto SSL para servidor

    Args:
        certfile: Certificado del servidor
        keyfile: Clave privada del servidor
        cafile: CA para verificar clientes (si require_client_cert=True)
        require_client_cert: Requerir certificado de cliente
        logger: Logger para mensajes

    Returns:
        Contexto SSL para servidor
    """
    verify_mode = ssl.CERT_REQUIRED if require_client_cert else ssl.CERT_NONE

    context = create_tls_context(
        purpose=ssl.Purpose.CLIENT_AUTH,
        certfile=certfile,
        keyfile=keyfile,
        cafile=cafile,
        verify_mode=verify_mode,
        check_hostname=False,  # El servidor no verifica hostname del cliente
        logger=logger
    )

    return context


def create_client_context(
    certfile: Optional[Path] = None,
    keyfile: Optional[Path] = None,
    cafile: Optional[Path] = None,
    verify_server: bool = True,
    logger: Optional[logging.Logger] = None
) -> ssl.SSLContext:
    """
    Crea un contexto SSL para cliente

    Args:
        certfile: Certificado del cliente (para autenticación mutua)
        keyfile: Clave privada del cliente (para autenticación mutua)
        cafile: CA para verificar servidor
        verify_server: Verificar certificado del servidor
        logger: Logger para mensajes

    Returns:
        Contexto SSL para cliente
    """
    if not verify_server:
        # No verificar servidor (solo para desarrollo/testing)
        verify_mode = ssl.CERT_NONE
        check_hostname = False
    else:
        verify_mode = ssl.CERT_REQUIRED
        check_hostname = True

    context = create_tls_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        certfile=certfile,
        keyfile=keyfile,
        cafile=cafile,
        verify_mode=verify_mode,
        check_hostname=check_hostname,
        logger=logger
    )

    return context
