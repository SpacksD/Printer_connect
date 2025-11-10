"""
Punto de entrada principal del cliente Printer_connect
"""

import sys
from pathlib import Path
import os

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.utils.logger import setup_logger
from client.utils.config import ConfigManager
from client.network.client import PrintClient
from shared.data_models import PrintParameters, PrintJobMetadata


def main():
    """Función principal"""
    print("=" * 60)
    print(" Printer_connect - Cliente")
    print(" Versión 0.1.0 (MVP)")
    print("=" * 60)
    print()

    # Cargar configuración
    config_file = Path(__file__).parent / 'config.ini'
    print(f"Cargando configuración desde: {config_file}")

    config = ConfigManager(config_file)

    # Configurar logging
    log_file = Path(config.get('Logging', 'log_file', './logs/client.log'))
    log_level = config.get('Logging', 'log_level', 'INFO')

    logger = setup_logger(log_file=log_file, log_level=log_level)
    logger.info("=" * 60)
    logger.info("Iniciando Printer_connect Client v0.1.0")
    logger.info("=" * 60)

    # Obtener parámetros del cliente
    server_host, server_port = config.get_server_address()
    client_id = config.get('Client', 'client_id')
    user = os.getenv('USER', os.getenv('USERNAME', 'unknown'))

    logger.info(f"Configuración:")
    logger.info(f"  - Servidor: {server_host}:{server_port}")
    logger.info(f"  - Client ID: {client_id}")
    logger.info(f"  - Usuario: {user}")

    print(f"\nServidor configurado: {server_host}:{server_port}")
    print(f"Client ID: {client_id}")
    print(f"Usuario: {user}")
    print()

    # Crear cliente
    client = PrintClient(
        server_host=server_host,
        server_port=server_port,
        logger=logger
    )

    # Probar conexión
    print("Probando conexión con el servidor...")
    if not client.test_connection():
        print("❌ No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo en:")
        print(f"   {server_host}:{server_port}")
        return

    print("✓ Conexión exitosa")
    print()

    # Crear archivo de prueba si no existe
    test_file = Path('./test_print.pdf')
    if not test_file.exists():
        print(f"Creando archivo de prueba: {test_file}")
        with open(test_file, 'wb') as f:
            # PDF mínimo válido
            f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n')
            f.write(b'2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n')
            f.write(b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n')
            f.write(b'xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n')
            f.write(b'0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\n')
            f.write(b'startxref\n190\n%%EOF')
        logger.info(f"Archivo de prueba creado: {test_file}")

    # Preparar parámetros de impresión
    parameters = PrintParameters()
    metadata = PrintJobMetadata(
        document_name=test_file.name,
        page_count=1,
        application="Printer_connect Client Test",
        file_size_bytes=test_file.stat().st_size
    )

    # Enviar trabajo de impresión
    print("-" * 60)
    print("Enviando trabajo de impresión de prueba...")
    print(f"Archivo: {test_file}")
    print(f"Tamaño: {test_file.stat().st_size} bytes")
    print()

    try:
        response = client.send_print_job(
            client_id=client_id,
            user=user,
            file_path=test_file,
            parameters=parameters,
            metadata=metadata
        )

        print("=" * 60)
        print(" RESPUESTA DEL SERVIDOR")
        print("=" * 60)
        print(f"Estado: {response['status'].upper()}")
        print(f"Mensaje: {response['message']}")

        if response.get('job_id'):
            print(f"Job ID: {response['job_id']}")
        if response.get('queue_position'):
            print(f"Posición en cola: {response['queue_position']}")

        print("=" * 60)

        if response['status'] == 'success':
            print("\n✓ Trabajo de impresión enviado exitosamente")
        else:
            print("\n❌ Error al enviar trabajo de impresión")
            if response.get('error_code'):
                print(f"Código de error: {response['error_code']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error enviando trabajo: {e}", exc_info=True)


if __name__ == '__main__':
    main()
