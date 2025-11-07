"""
Punto de entrada principal del servidor Printer_connect
"""

import sys
from pathlib import Path
import signal

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.utils.logger import setup_logger
from server.utils.config import ConfigManager
from server.network.server import PrintServer


def signal_handler(signum, frame):
    """Manejador de señales para cierre limpio"""
    print("\nSeñal de terminación recibida. Cerrando servidor...")
    sys.exit(0)


def main():
    """Función principal"""
    print("=" * 60)
    print(" Printer_connect - Servidor")
    print(" Versión 0.1.0 (MVP)")
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
    logger.info("Iniciando Printer_connect Server v0.1.0")
    logger.info("=" * 60)

    # Obtener parámetros del servidor
    host, port = config.get_server_address()
    temp_folder = Path(config.get('Printer', 'temp_folder', './temp'))

    logger.info(f"Configuración:")
    logger.info(f"  - Host: {host}")
    logger.info(f"  - Puerto: {port}")
    logger.info(f"  - Carpeta temporal: {temp_folder}")
    logger.info(f"  - Nivel de log: {log_level}")

    print(f"\nServidor iniciando en {host}:{port}")
    print(f"Carpeta temporal: {temp_folder}")
    print(f"Log: {log_file}")
    print()
    print("Presiona Ctrl+C para detener el servidor")
    print("-" * 60)
    print()

    # Crear y arrancar servidor
    server = PrintServer(
        host=host,
        port=port,
        temp_folder=temp_folder,
        logger=logger
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por usuario")
        logger.info("Servidor interrumpido por usuario")
    except Exception as e:
        print(f"\nError fatal: {e}")
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        server.stop()
        logger.info("Servidor detenido")
        print("\nServidor cerrado correctamente")


if __name__ == '__main__':
    main()
