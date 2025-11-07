"""
Punto de entrada principal del servidor Printer_connect V3
Incluye base de datos, cola de impresión e impresora física
"""

import sys
from pathlib import Path
import signal

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.utils.logger import setup_logger
from server.utils.config import ConfigManager
from server.network.server_v3 import PrintServerV3
from server.database.database import Database
from server.printer.printer_manager import PrinterManager
from server.printer.job_processor import JobProcessor


# Variable global para el servidor (para signal handler)
server_instance = None


def signal_handler(signum, frame):
    """Manejador de señales para cierre limpio"""
    print("\nSeñal de terminación recibida. Cerrando servidor...")
    if server_instance:
        server_instance.stop()
    sys.exit(0)


def main():
    """Función principal"""
    global server_instance

    print("=" * 60)
    print(" Printer_connect - Servidor V3")
    print(" Versión 0.3.0")
    print(" + Base de Datos")
    print(" + Cola de Impresión")
    print(" + Impresora Física")
    print("=" * 60)
    print()

    # Configurar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Cargar configuración
    config_file = Path(__file__).parent / 'config.ini'
    print(f"Cargando configuración desde: {config_file}")

    config = ConfigManager(config_file)

    # Configurar logging
    log_file = Path(config.get('Logging', 'log_file', './logs/server.log'))
    log_level = config.get('Logging', 'log_level', 'INFO')

    logger = setup_logger(log_file=log_file, log_level=log_level)
    logger.info("=" * 60)
    logger.info("Iniciando Printer_connect Server V3")
    logger.info("=" * 60)

    # Obtener parámetros del servidor
    host, port = config.get_server_address()
    temp_folder = Path(config.get('Printer', 'temp_folder', './temp'))

    # Base de datos
    db_type = config.get('Database', 'db_type', 'sqlite')
    if db_type == 'sqlite':
        db_file = Path(config.get('Database', 'sqlite_file', './data/printer_connect.db'))
        db_url = f"sqlite:///{db_file}"
    else:
        # PostgreSQL (configurar en config.ini)
        db_host = config.get('Database', 'postgresql_host', 'localhost')
        db_port = config.get('Database', 'postgresql_port', '5432')
        db_name = config.get('Database', 'postgresql_database', 'printer_connect')
        db_user = config.get('Database', 'postgresql_user', 'printer')
        db_pass = config.get('Database', 'postgresql_password', '')
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Impresora
    printer_name = config.get('Printer', 'printer_name', '')

    logger.info(f"Configuración:")
    logger.info(f"  - Host: {host}")
    logger.info(f"  - Puerto: {port}")
    logger.info(f"  - Carpeta temporal: {temp_folder}")
    logger.info(f"  - Base de datos: {db_url}")
    logger.info(f"  - Impresora: {printer_name or 'Auto-detect'}")
    logger.info(f"  - Nivel de log: {log_level}")

    print(f"\nServidor iniciando en {host}:{port}")
    print(f"Base de datos: {db_type}")
    print(f"Carpeta temporal: {temp_folder}")
    print(f"Impresora: {printer_name or 'Auto-detect'}")
    print(f"Log: {log_file}")
    print()

    # Crear componentes
    print("Inicializando componentes...")

    # 1. Base de datos
    print("  [1/4] Base de datos...")
    database = Database(db_url=db_url, logger=logger)

    # 2. Gestor de impresora
    print("  [2/4] Gestor de impresora...")
    # Determinar si usar mock
    use_mock = not printer_name  # Si no hay impresora configurada, usar mock

    printer_manager = PrinterManager(
        printer_name=printer_name or None,
        use_mock=use_mock,
        logger=logger
    )

    # Mostrar impresoras disponibles
    printers = printer_manager.get_printers()
    logger.info(f"Impresoras disponibles: {printers}")
    print(f"  Impresoras disponibles: {printers}")

    # 3. Procesador de trabajos
    print("  [3/4] Procesador de trabajos...")
    job_processor = JobProcessor(
        database=database,
        printer_manager=printer_manager,
        logger=logger
    )

    # 4. Servidor TCP/IP
    print("  [4/4] Servidor TCP/IP...")
    server = PrintServerV3(
        host=host,
        port=port,
        temp_folder=temp_folder,
        database=database,
        job_processor=job_processor,
        logger=logger
    )

    server_instance = server

    print()
    print("✓ Todos los componentes inicializados")
    print()
    print("Presiona Ctrl+C para detener el servidor")
    print("-" * 60)
    print()

    # Iniciar servidor
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por usuario")
        logger.info("Servidor interrumpido por usuario")
    except Exception as e:
        print(f"\nError fatal: {e}")
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        logger.info("Servidor detenido")
        print("\nServidor cerrado correctamente")


if __name__ == '__main__':
    main()
