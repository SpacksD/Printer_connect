#!/usr/bin/env python3
"""
Script de prueba end-to-end para la Fase 1 (MVP)
Verifica que la comunicación cliente-servidor funciona correctamente
"""

import sys
import time
import threading
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.network.server import PrintServer
from client.network.client import PrintClient
from shared.data_models import PrintParameters, PrintJobMetadata
import logging


def run_server(port=9100):
    """Ejecuta el servidor en un thread"""
    logging.basicConfig(
        level=logging.INFO,
        format='[SERVER] %(message)s'
    )

    temp_folder = Path('./test_temp')
    server = PrintServer(
        host='127.0.0.1',
        port=port,
        temp_folder=temp_folder
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


def run_client_test(port=9100):
    """Ejecuta el cliente de prueba"""
    logging.basicConfig(
        level=logging.INFO,
        format='[CLIENT] %(message)s'
    )

    # Esperar a que el servidor esté listo
    print("\n[TEST] Esperando a que el servidor esté listo...")
    time.sleep(2)

    # Crear cliente
    client = PrintClient(
        server_host='127.0.0.1',
        server_port=port
    )

    # Probar conexión
    print("[TEST] Probando conexión...")
    if not client.test_connection():
        print("[TEST] ❌ ERROR: No se pudo conectar al servidor")
        return False

    print("[TEST] ✓ Conexión exitosa")

    # Crear archivo de prueba
    test_file = Path('./test_document.pdf')
    with open(test_file, 'wb') as f:
        f.write(b'%PDF-1.4\nTest PDF Content\n%%EOF')

    print(f"[TEST] Archivo de prueba creado: {test_file}")

    # Preparar trabajo de impresión
    parameters = PrintParameters()
    metadata = PrintJobMetadata(
        document_name="test_document.pdf",
        page_count=1,
        application="Phase 1 Test",
        file_size_bytes=test_file.stat().st_size
    )

    # Enviar trabajo
    print("\n[TEST] Enviando trabajo de impresión...")
    try:
        response = client.send_print_job(
            client_id="TEST-CLIENT-001",
            user="test_user",
            file_path=test_file,
            parameters=parameters,
            metadata=metadata
        )

        print("\n" + "=" * 60)
        print(" RESULTADO DEL TEST")
        print("=" * 60)
        print(f"Estado: {response['status']}")
        print(f"Mensaje: {response['message']}")

        if response.get('job_id'):
            print(f"Job ID: {response['job_id']}")
        if response.get('queue_position'):
            print(f"Posición en cola: {response['queue_position']}")

        print("=" * 60)

        if response['status'] == 'success':
            print("\n[TEST] ✓ FASE 1 (MVP) COMPLETADA EXITOSAMENTE")
            print("[TEST] ✓ La comunicación cliente-servidor funciona correctamente")
            return True
        else:
            print("\n[TEST] ❌ ERROR: El servidor reportó un error")
            return False

    except Exception as e:
        print(f"\n[TEST] ❌ ERROR: {e}")
        return False
    finally:
        # Limpiar
        if test_file.exists():
            test_file.unlink()


def main():
    """Función principal"""
    print("=" * 60)
    print(" TEST FASE 1 (MVP) - Printer_connect")
    print(" Comunicación Cliente-Servidor")
    print("=" * 60)

    port = 9101  # Usar puerto diferente para testing

    # Iniciar servidor en thread separado
    print("\n[TEST] Iniciando servidor de prueba...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    try:
        # Ejecutar pruebas del cliente
        success = run_client_test(port)

        # Resultado final
        print("\n" + "=" * 60)
        if success:
            print(" ✓✓✓ TODAS LAS PRUEBAS PASARON ✓✓✓")
            print(" La Fase 1 (MVP) está completa y funcionando")
        else:
            print(" ❌❌❌ ALGUNAS PRUEBAS FALLARON ❌❌❌")
            print(" Revisa los logs para más detalles")
        print("=" * 60)

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n[TEST] Test interrumpido por usuario")
        return 1
    except Exception as e:
        print(f"\n[TEST] Error fatal: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
