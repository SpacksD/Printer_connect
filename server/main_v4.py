"""
Punto de entrada principal del servidor seguro (Fase 4)
Inicializa y arranca todos los componentes con seguridad
"""

import sys
import signal
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.utils.config import ConfigManager
from server.database.database import DatabaseManager
from server.printer.printer_manager import PrinterManager
from server.printer.queue_manager import PrintQueueManager
from server.printer.job_processor import JobProcessor
from server.network.server_v4 import SecurePrintServer
from shared.security.auth import AuthenticationManager


def setup_logging(config: ConfigManager) -> logging.Logger:
    """Configura el sistema de logging"""
    log_level = config.get('Logging', 'level', 'INFO')
    log_file = config.get('Logging', 'file', 'server_secure.log')

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def main():
    """Función principal"""
    print("=" * 60)
    print(" Printer_connect - Servidor Seguro (Fase 4)")
    print(" Versión 0.4.0")
    print("=" * 60)
    print()

    # Cargar configuración
    config_file = Path(__file__).parent / 'config.ini'
    config = ConfigManager(config_file)

    # Setup logging
    logger = setup_logging(config)

    logger.info("Iniciando Printer_connect Servidor Seguro...")

    try:
        # 1. Base de datos
        logger.info("[1/6] Inicializando base de datos...")
        db_url = config.get('Database', 'url', 'sqlite:///printer_connect.db')
        db_manager = DatabaseManager(db_url, logger=logger)

        print(f"✓ Base de datos: {db_url}")

        # 2. Printer Manager
        logger.info("[2/6] Inicializando printer manager...")
        printer_name = config.get('Printer', 'name', fallback=None)
        use_mock = config.getboolean('Printer', 'use_mock', fallback=True)

        printer_manager = PrinterManager(
            printer_name=printer_name,
            use_mock=use_mock,
            logger=logger
        )

        available_printers = printer_manager.get_printers()
        print(f"✓ Printer manager inicializado")
        print(f"  - Impresoras disponibles: {len(available_printers)}")
        if available_printers:
            print(f"  - Impresora seleccionada: {printer_manager.printer_name}")

        # 3. Print Queue Manager
        logger.info("[3/6] Inicializando cola de impresión...")
        queue_manager = PrintQueueManager(logger=logger)

        print("✓ Cola de impresión inicializada")

        # 4. Job Processor
        logger.info("[4/6] Inicializando procesador de trabajos...")
        job_processor = JobProcessor(
            db_manager=db_manager,
            printer_manager=printer_manager,
            queue_manager=queue_manager,
            logger=logger
        )

        # Iniciar procesamiento
        job_processor.start_processing()

        print("✓ Procesador de trabajos inicializado")

        # 5. Authentication Manager
        logger.info("[5/6] Inicializando gestor de autenticación...")

        # Cargar o generar secret key
        secret_key = config.get('Security', 'jwt_secret_key', fallback=None)
        token_expiration_hours = config.getint(
            'Security',
            'token_expiration_hours',
            fallback=24
        )

        auth_manager = AuthenticationManager(
            secret_key=secret_key,
            token_expiration_hours=token_expiration_hours,
            logger=logger
        )

        print("✓ Gestor de autenticación inicializado")
        print(f"  - Expiración de tokens: {token_expiration_hours}h")

        # 6. Servidor Seguro
        logger.info("[6/6] Inicializando servidor seguro...")

        # Configuración del servidor
        host = config.get('Server', 'host', '0.0.0.0')
        port = config.getint('Server', 'port', 9100)

        # Configuración TLS
        tls_enabled = config.getboolean('Security', 'tls_enabled', fallback=True)

        if not tls_enabled:
            logger.error("TLS está deshabilitado. Fase 4 requiere TLS.")
            print("❌ ERROR: TLS está deshabilitado en config.ini")
            print("   La Fase 4 requiere TLS para seguridad.")
            print("   Habilita TLS en [Security] tls_enabled = true")
            sys.exit(1)

        cert_dir = Path(config.get('Security', 'cert_dir', 'certs'))
        certfile = cert_dir / config.get('Security', 'certfile', 'server.crt')
        keyfile = cert_dir / config.get('Security', 'keyfile', 'server.key')
        cafile_name = config.get('Security', 'cafile', fallback=None)
        cafile = (cert_dir / cafile_name) if cafile_name else None

        # Verificar que existen los certificados
        if not certfile.exists():
            logger.error(f"Certificado no encontrado: {certfile}")
            print(f"❌ ERROR: Certificado no encontrado: {certfile}")
            print()
            print("Genera certificados con:")
            print(f"  python scripts/generate_certificates.py --server --hostname {host}")
            sys.exit(1)

        if not keyfile.exists():
            logger.error(f"Clave privada no encontrada: {keyfile}")
            print(f"❌ ERROR: Clave privada no encontrada: {keyfile}")
            sys.exit(1)

        # Rate limiting
        enable_rate_limiting = config.getboolean(
            'Security',
            'enable_rate_limiting',
            fallback=True
        )
        requests_per_minute = config.getint(
            'Security',
            'requests_per_minute',
            fallback=60
        )

        # Tamaño máximo de archivo
        max_file_size = config.getint(
            'Security',
            'max_file_size_mb',
            fallback=100
        ) * 1024 * 1024

        # Crear servidor
        server = SecurePrintServer(
            host=host,
            port=port,
            database_manager=db_manager,
            job_processor=job_processor,
            auth_manager=auth_manager,
            certfile=certfile,
            keyfile=keyfile,
            cafile=cafile,
            require_client_cert=False,
            enable_rate_limiting=enable_rate_limiting,
            requests_per_minute=requests_per_minute,
            max_file_size=max_file_size,
            logger=logger
        )

        print("✓ Servidor seguro inicializado")
        print()
        print("-" * 60)
        print("CONFIGURACIÓN:")
        print(f"  Host: {host}")
        print(f"  Puerto: {port}")
        print(f"  TLS: Habilitado")
        print(f"  Certificado: {certfile}")
        print(f"  Autenticación: JWT requerido")
        print(f"  Rate limiting: {'Habilitado' if enable_rate_limiting else 'Deshabilitado'}")
        if enable_rate_limiting:
            print(f"  Requests/min: {requests_per_minute}")
        print(f"  Max file size: {max_file_size / (1024*1024):.0f} MB")
        print("-" * 60)
        print()

        # Generar token de ejemplo para testing
        print("TOKEN DE EJEMPLO PARA TESTING:")
        print()
        example_token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user',
            roles=['user']
        )
        print(f"  {example_token}")
        print()
        print("  Usa este token en el cliente con:")
        print(f"    client.set_auth_token('{example_token}')")
        print()
        print("-" * 60)
        print()

        # Configurar manejo de señales
        def signal_handler(signum, frame):
            logger.info("Señal de interrupción recibida")
            print()
            print("Deteniendo servidor...")
            job_processor.stop_processing()
            server.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar servidor
        logger.info("Iniciando servidor...")
        print("🔒 Servidor seguro iniciado exitosamente")
        print("Presiona Ctrl+C para detener")
        print()

        server.start()

    except KeyboardInterrupt:
        print()
        logger.info("Interrupción por usuario")
        print("Deteniendo servidor...")

    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        print()
        print(f"❌ ERROR CRÍTICO: {e}")
        print()
        print("Ver logs para más detalles")
        sys.exit(1)


if __name__ == '__main__':
    main()
