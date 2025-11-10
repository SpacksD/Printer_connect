"""
Servidor TCP/IP con TLS y autenticación JWT (Fase 4)
Versión segura del servidor de impresión
"""

import sys
import socket
import ssl
import struct
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import Protocol, Message
from shared.data_models import PrintJob, ServerResponse, ResponseCode
from shared.security.tls_wrapper import TLSSocketWrapper, create_server_context
from shared.security.auth import AuthenticationManager, TokenValidator, AuthenticationError
from shared.security.validation import InputValidator, ValidationError
from shared.security.rate_limiter import RateLimiter, RateLimitExceeded

from server.database.database import DatabaseManager
from server.printer.job_processor import JobProcessor


class SecurePrintServer:
    """
    Servidor de impresión seguro con TLS y autenticación
    """

    def __init__(
        self,
        host: str,
        port: int,
        database_manager: DatabaseManager,
        job_processor: JobProcessor,
        auth_manager: AuthenticationManager,
        certfile: Path,
        keyfile: Path,
        cafile: Optional[Path] = None,
        require_client_cert: bool = False,
        enable_rate_limiting: bool = True,
        requests_per_minute: int = 60,
        max_file_size: int = 100 * 1024 * 1024,  # 100 MB
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el servidor seguro

        Args:
            host: Dirección del servidor
            port: Puerto del servidor
            database_manager: Gestor de base de datos
            job_processor: Procesador de trabajos
            auth_manager: Gestor de autenticación
            certfile: Certificado del servidor
            keyfile: Clave privada del servidor
            cafile: CA para verificar clientes (opcional)
            require_client_cert: Requerir certificado de cliente
            enable_rate_limiting: Habilitar rate limiting
            requests_per_minute: Límite de requests por minuto
            max_file_size: Tamaño máximo de archivo
            logger: Logger para mensajes
        """
        self.host = host
        self.port = port
        self.db_manager = database_manager
        self.job_processor = job_processor
        self.auth_manager = auth_manager
        self.logger = logger or logging.getLogger(__name__)

        # Configuración TLS
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile
        self.require_client_cert = require_client_cert

        # Socket y contexto TLS
        self.server_socket: Optional[socket.socket] = None
        self.tls_context: Optional[ssl.SSLContext] = None
        self.running = False

        # Validación y rate limiting
        self.validator = InputValidator(
            max_file_size=max_file_size,
            logger=self.logger
        )

        self.token_validator = TokenValidator(
            auth_manager=self.auth_manager,
            logger=self.logger
        )

        if enable_rate_limiting:
            self.rate_limiter = RateLimiter(
                requests_per_minute=requests_per_minute,
                logger=self.logger
            )
        else:
            self.rate_limiter = None

        # Estadísticas
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_jobs_received': 0,
            'authentication_failures': 0,
            'rate_limit_exceeded': 0,
            'validation_errors': 0
        }
        self.stats_lock = threading.RLock()

        self.logger.info(
            f"SecurePrintServer inicializado en {host}:{port} "
            f"(TLS enabled, auth required)"
        )

    def start(self):
        """Inicia el servidor"""
        self.logger.info(f"Iniciando servidor seguro en {self.host}:{self.port}")

        try:
            # Crear contexto TLS
            self.tls_context = create_server_context(
                certfile=self.certfile,
                keyfile=self.keyfile,
                cafile=self.cafile,
                require_client_cert=self.require_client_cert,
                logger=self.logger
            )

            # Crear socket del servidor
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            self.running = True

            self.logger.info(f"✓ Servidor escuchando en {self.host}:{self.port} (TLS)")
            self.logger.info(f"  - Certificado: {self.certfile}")
            self.logger.info(f"  - Autenticación: JWT requerido")
            self.logger.info(f"  - Rate limiting: {'Habilitado' if self.rate_limiter else 'Deshabilitado'}")

            # Loop principal
            while self.running:
                try:
                    # Aceptar conexión
                    client_socket, client_address = self.server_socket.accept()

                    with self.stats_lock:
                        self.stats['total_connections'] += 1

                    self.logger.info(f"Nueva conexión desde {client_address}")

                    # Envolver con TLS y manejar en thread separado
                    try:
                        tls_socket = TLSSocketWrapper(
                            sock=client_socket,
                            context=self.tls_context,
                            server_side=True,
                            logger=self.logger
                        )

                        # Crear thread para manejar el cliente
                        client_thread = threading.Thread(
                            target=self._handle_client,
                            args=(tls_socket, client_address),
                            daemon=True
                        )
                        client_thread.start()

                    except ssl.SSLError as e:
                        self.logger.error(f"Error TLS con {client_address}: {e}")
                        client_socket.close()

                except KeyboardInterrupt:
                    self.logger.info("Interrupción por teclado")
                    break

                except Exception as e:
                    self.logger.error(f"Error aceptando conexión: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error iniciando servidor: {e}", exc_info=True)
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

    def _handle_client(
        self,
        client_socket: TLSSocketWrapper,
        client_address: tuple
    ):
        """
        Maneja la comunicación con un cliente

        Args:
            client_socket: Socket TLS del cliente
            client_address: Dirección del cliente
        """
        with self.stats_lock:
            self.stats['active_connections'] += 1

        try:
            self.logger.info(f"Manejando cliente {client_address}")

            # Leer mensaje
            message_data = self._receive_message(client_socket)

            if not message_data:
                self.logger.warning(f"Cliente {client_address} envió mensaje vacío")
                self._send_error_response(
                    client_socket,
                    "Mensaje vacío",
                    ResponseCode.ERROR
                )
                return

            # Decodificar mensaje
            message = Message.from_dict(message_data)

            # Procesar mensaje
            response = self._process_message(message, client_address)

            # Enviar respuesta
            self._send_response(client_socket, response)

        except Exception as e:
            self.logger.error(
                f"Error manejando cliente {client_address}: {e}",
                exc_info=True
            )
            self._send_error_response(
                client_socket,
                f"Error del servidor: {str(e)}",
                ResponseCode.ERROR
            )

        finally:
            with self.stats_lock:
                self.stats['active_connections'] -= 1

            try:
                client_socket.close()
            except Exception:
                pass

    def _receive_message(self, client_socket: TLSSocketWrapper) -> Optional[dict]:
        """
        Recibe un mensaje del cliente

        Args:
            client_socket: Socket del cliente

        Returns:
            Dictionary con el mensaje o None si falla
        """
        try:
            # Leer longitud del mensaje (4 bytes)
            length_bytes = self._recv_exactly(client_socket, 4)
            if not length_bytes:
                return None

            message_length = struct.unpack('!I', length_bytes)[0]

            # Validar longitud
            MAX_MESSAGE_SIZE = 200 * 1024 * 1024  # 200 MB
            if message_length > MAX_MESSAGE_SIZE:
                raise ValidationError(f"Mensaje demasiado grande: {message_length} bytes")

            # Leer mensaje completo
            message_bytes = self._recv_exactly(client_socket, message_length)
            if not message_bytes:
                return None

            # Decodificar JSON
            message_json = message_bytes.decode('utf-8')
            return Protocol.decode_json(message_json)

        except Exception as e:
            self.logger.error(f"Error recibiendo mensaje: {e}")
            return None

    def _recv_exactly(self, sock: TLSSocketWrapper, n: int) -> Optional[bytes]:
        """
        Recibe exactamente n bytes

        Args:
            sock: Socket
            n: Número de bytes a recibir

        Returns:
            Bytes recibidos o None si falla
        """
        data = b''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _process_message(
        self,
        message: Message,
        client_address: tuple
    ) -> ServerResponse:
        """
        Procesa un mensaje del cliente

        Args:
            message: Mensaje recibido
            client_address: Dirección del cliente

        Returns:
            ServerResponse con el resultado
        """
        try:
            # Validar token de autenticación
            token = message.headers.get('Authorization', '').replace('Bearer ', '')

            if not token:
                with self.stats_lock:
                    self.stats['authentication_failures'] += 1

                return ServerResponse(
                    status=ResponseCode.UNAUTHORIZED.value,
                    message="Token de autenticación requerido",
                    data={'error': 'missing_token'}
                )

            # Validar token
            try:
                token_payload = self.token_validator.validate(token)
                client_id = token_payload.get('client_id')

            except AuthenticationError as e:
                with self.stats_lock:
                    self.stats['authentication_failures'] += 1

                self.logger.warning(f"Autenticación fallida: {e}")

                return ServerResponse(
                    status=ResponseCode.UNAUTHORIZED.value,
                    message=f"Autenticación fallida: {str(e)}",
                    data={'error': 'invalid_token'}
                )

            # Rate limiting
            if self.rate_limiter:
                try:
                    self.rate_limiter.check_rate_limit(client_id)

                except RateLimitExceeded as e:
                    with self.stats_lock:
                        self.stats['rate_limit_exceeded'] += 1

                    return ServerResponse(
                        status=ResponseCode.ERROR.value,
                        message=str(e),
                        data={'error': 'rate_limit_exceeded'}
                    )

            # Procesar según el tipo de mensaje
            if message.type == 'print_job':
                return self._handle_print_job(message, client_id, token_payload)

            elif message.type == 'ping':
                return self._handle_ping(message, client_id)

            elif message.type == 'status':
                return self._handle_status(message, client_id)

            else:
                return ServerResponse(
                    status=ResponseCode.ERROR.value,
                    message=f"Tipo de mensaje no soportado: {message.type}",
                    data={'error': 'invalid_message_type'}
                )

        except ValidationError as e:
            with self.stats_lock:
                self.stats['validation_errors'] += 1

            self.logger.warning(f"Error de validación: {e}")

            return ServerResponse(
                status=ResponseCode.ERROR.value,
                message=f"Error de validación: {str(e)}",
                data={'error': 'validation_error'}
            )

        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}", exc_info=True)

            return ServerResponse(
                status=ResponseCode.ERROR.value,
                message=f"Error del servidor: {str(e)}",
                data={'error': 'server_error'}
            )

    def _handle_print_job(
        self,
        message: Message,
        client_id: str,
        token_payload: Dict[str, Any]
    ) -> ServerResponse:
        """
        Maneja un trabajo de impresión

        Args:
            message: Mensaje con el trabajo
            client_id: ID del cliente
            token_payload: Payload del token JWT

        Returns:
            ServerResponse con el resultado
        """
        try:
            # Extraer print job del mensaje
            print_job_data = message.body

            # Validar campos requeridos
            self.validator.validate_client_id(client_id)

            if 'user' in print_job_data:
                self.validator.validate_username(print_job_data['user'])

            # Crear PrintJob
            print_job = PrintJob.from_dict(print_job_data)

            # Validar archivo si viene incluido
            if message.file_data:
                # Guardar archivo temporalmente
                temp_dir = Path('/tmp/printer_connect_secure')
                temp_dir.mkdir(parents=True, exist_ok=True)

                file_path = temp_dir / f"{print_job.job_id}.pdf"
                with open(file_path, 'wb') as f:
                    f.write(message.file_data)

                # Validar archivo
                self.validator.validate_file_path(file_path)

                print_job.file_path = str(file_path)

            # Registrar en base de datos
            with self.db_manager.session_scope() as session:
                db_job = self.db_manager.create_print_job(
                    session=session,
                    job_id=print_job.job_id,
                    client_id=client_id,
                    user=print_job.user,
                    file_path=print_job.file_path,
                    parameters=print_job.parameters,
                    metadata=print_job.metadata
                )

            # Enviar a procesador
            position = self.job_processor.submit_job(
                job_id=print_job.job_id,
                priority=print_job.metadata.priority if print_job.metadata else 5
            )

            with self.stats_lock:
                self.stats['total_jobs_received'] += 1

            self.logger.info(
                f"Trabajo recibido: {print_job.job_id} de {client_id}, "
                f"posición en cola: {position}"
            )

            return ServerResponse(
                status=ResponseCode.SUCCESS.value,
                message="Trabajo recibido exitosamente",
                data={
                    'job_id': print_job.job_id,
                    'queue_position': position,
                    'client_id': client_id
                }
            )

        except Exception as e:
            self.logger.error(f"Error manejando print job: {e}", exc_info=True)
            raise

    def _handle_ping(self, message: Message, client_id: str) -> ServerResponse:
        """Maneja un ping del cliente"""
        return ServerResponse(
            status=ResponseCode.SUCCESS.value,
            message="pong",
            data={
                'server_time': datetime.now().isoformat(),
                'client_id': client_id
            }
        )

    def _handle_status(self, message: Message, client_id: str) -> ServerResponse:
        """Maneja una solicitud de estado"""
        with self.stats_lock:
            stats_copy = self.stats.copy()

        # Agregar stats del job processor
        queue_stats = self.job_processor.get_queue_stats()
        stats_copy.update(queue_stats)

        return ServerResponse(
            status=ResponseCode.SUCCESS.value,
            message="Estado del servidor",
            data=stats_copy
        )

    def _send_response(
        self,
        client_socket: TLSSocketWrapper,
        response: ServerResponse
    ):
        """
        Envía una respuesta al cliente

        Args:
            client_socket: Socket del cliente
            response: Respuesta a enviar
        """
        try:
            # Convertir respuesta a mensaje
            message = Message(
                type='response',
                body=response.to_dict()
            )

            # Codificar y enviar
            response_bytes = Protocol.encode_message(message)
            client_socket.sendall(response_bytes)

        except Exception as e:
            self.logger.error(f"Error enviando respuesta: {e}")

    def _send_error_response(
        self,
        client_socket: TLSSocketWrapper,
        error_message: str,
        code: ResponseCode = ResponseCode.ERROR
    ):
        """
        Envía una respuesta de error

        Args:
            client_socket: Socket del cliente
            error_message: Mensaje de error
            code: Código de respuesta
        """
        response = ServerResponse(
            status=code.value,
            message=error_message,
            data={'error': True}
        )

        self._send_response(client_socket, response)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servidor"""
        with self.stats_lock:
            return self.stats.copy()
