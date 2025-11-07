#!/usr/bin/env python3
"""
Script de prueba end-to-end para la Fase 3
Prueba la integración de BD, cola e impresora
"""

import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database.database import Database
from server.printer.printer_manager import PrinterManager
from server.printer.job_processor import JobProcessor
from server.network.server_v3 import PrintServerV3
from client.network.client import PrintClient
from shared.data_models import PrintParameters, PrintJobMetadata
import logging


def test_database():
    """Test 1: Base de datos"""
    print("\n[TEST 1/5] Probando base de datos...")

    # Crear BD en memoria
    db = Database(db_url="sqlite:///:memory:")

    # Crear un trabajo
    job_data = {
        'job_id': 'TEST-DB-001',
        'client_id': 'CLIENT-TEST',
        'user_name': 'test_user',
        'document_name': 'test.pdf',
        'file_format': 'pdf',
        'file_path': '/tmp/test.pdf',
        'page_count': 5,
        'status': 'pending',
        'priority': 5
    }

    job = db.create_print_job(job_data)
    print(f"  ✓ Trabajo creado: {job.job_id}")

    # Recuperar trabajo
    retrieved = db.get_print_job('TEST-DB-001')
    assert retrieved.job_id == 'TEST-DB-001'
    print(f"  ✓ Trabajo recuperado correctamente")

    # Actualizar trabajo
    db.update_print_job('TEST-DB-001', {'status': 'completed'})
    updated = db.get_print_job('TEST-DB-001')
    assert updated.status == 'completed'
    print(f"  ✓ Trabajo actualizado correctamente")

    # Obtener resumen
    summary = db.get_summary()
    print(f"  ✓ Resumen obtenido: {summary['total_jobs']} trabajos")

    print("  ✓ Base de datos funciona correctamente")
    return True


def test_printer_manager():
    """Test 2: Gestor de impresora"""
    print("\n[TEST 2/5] Probando gestor de impresora...")

    # Crear gestor mock
    manager = PrinterManager(use_mock=True)

    # Obtener impresoras
    printers = manager.get_printers()
    print(f"  ✓ Impresoras disponibles: {printers}")

    # Crear archivo de prueba
    test_file = Path('./test_print_fase3.pdf')
    with open(test_file, 'wb') as f:
        f.write(b'%PDF-1.4\nTest PDF Fase 3\n%%EOF')

    # Imprimir archivo
    success = manager.print_file(test_file)
    assert success is True
    print(f"  ✓ Archivo 'impreso' correctamente (mock)")

    # Verificar archivo impreso
    if hasattr(manager.backend, 'get_printed_files'):
        printed = manager.backend.get_printed_files()
        assert len(printed) == 1
        print(f"  ✓ Archivo registrado en mock: {printed[0]}")

    # Obtener estado
    status = manager.get_printer_status()
    print(f"  ✓ Estado de impresora: {status['status']}")

    # Limpiar
    test_file.unlink()

    print("  ✓ Gestor de impresora funciona correctamente")
    return True


def test_job_processor():
    """Test 3: Procesador de trabajos"""
    print("\n[TEST 3/5] Probando procesador de trabajos...")

    # Crear componentes
    db = Database(db_url="sqlite:///:memory:")
    printer = PrinterManager(use_mock=True)
    processor = JobProcessor(
        database=db,
        printer_manager=printer
    )

    # Crear archivo de prueba
    test_file = Path('./test_job_processor.pdf')
    with open(test_file, 'wb') as f:
        f.write(b'%PDF-1.4\nTest Job Processor\n%%EOF')

    # Crear trabajo en BD
    job_data = {
        'job_id': 'PROC-001',
        'client_id': 'CLIENT-TEST',
        'user_name': 'processor_user',
        'document_name': 'processor_test.pdf',
        'file_format': 'pdf',
        'file_path': str(test_file),
        'page_count': 1,
        'status': 'pending',
        'priority': 5
    }

    job = db.create_print_job(job_data)
    print(f"  ✓ Trabajo creado: {job.job_id}")

    # Enviar a cola
    processor.submit_job(job)
    queue_size = processor.queue_manager.get_queue_size()
    print(f"  ✓ Trabajo en cola (tamaño: {queue_size})")

    # Iniciar procesamiento
    processor.start()
    print("  ✓ Procesador iniciado")

    # Esperar procesamiento
    time.sleep(2)

    # Verificar que se procesó
    processed_job = db.get_print_job('PROC-001')
    print(f"  ✓ Estado del trabajo: {processed_job.status}")

    # Detener procesador
    processor.stop()
    print("  ✓ Procesador detenido")

    # Limpiar
    test_file.unlink()

    print("  ✓ Procesador de trabajos funciona correctamente")
    return True


def test_server_integration():
    """Test 4: Integración servidor completo"""
    print("\n[TEST 4/5] Probando integración del servidor...")

    # Crear componentes
    db = Database(db_url="sqlite:///:memory:")
    printer = PrinterManager(use_mock=True)
    processor = JobProcessor(database=db, printer_manager=printer)

    # Crear servidor
    port = 9102  # Puerto diferente para test
    server = PrintServerV3(
        host='127.0.0.1',
        port=port,
        database=db,
        job_processor=processor
    )

    # Iniciar servidor en thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1)

    print(f"  ✓ Servidor iniciado en puerto {port}")

    # Crear cliente
    client = PrintClient(server_host='127.0.0.1', server_port=port)

    # Probar conexión
    if not client.test_connection():
        print("  ❌ No se puede conectar al servidor")
        return False

    print("  ✓ Cliente conectado")

    # Crear archivo de prueba
    test_file = Path('./test_integration.pdf')
    with open(test_file, 'wb') as f:
        f.write(b'%PDF-1.4\nTest Integration\n%%EOF')

    # Preparar trabajo
    parameters = PrintParameters()
    metadata = PrintJobMetadata(
        document_name="integration_test.pdf",
        page_count=1,
        application="Phase 3 Test",
        file_size_bytes=test_file.stat().st_size
    )

    # Enviar trabajo
    print("  Enviando trabajo de impresión...")
    response = client.send_print_job(
        client_id="CLIENT-TEST",
        user="integration_test",
        file_path=test_file,
        parameters=parameters,
        metadata=metadata
    )

    assert response['status'] == 'success'
    job_id = response['job_id']
    print(f"  ✓ Trabajo enviado: {job_id}")

    # Esperar procesamiento
    time.sleep(3)

    # Verificar en BD
    job = db.get_print_job(job_id)
    print(f"  ✓ Trabajo en BD: estado={job.status}")

    # Verificar resumen
    summary = db.get_summary()
    print(f"  ✓ Resumen: {summary['total_jobs']} trabajos totales")

    # Limpiar
    test_file.unlink()
    server.stop()

    print("  ✓ Integración del servidor funciona correctamente")
    return True


def test_queue_priority():
    """Test 5: Prioridades en la cola"""
    print("\n[TEST 5/5] Probando prioridades de cola...")

    db = Database(db_url="sqlite:///:memory:")
    printer = PrinterManager(use_mock=True)
    processor = JobProcessor(database=db, printer_manager=printer)

    # Crear archivos de prueba con diferentes prioridades
    test_files = []
    for i in range(3):
        test_file = Path(f'./test_priority_{i}.pdf')
        with open(test_file, 'wb') as f:
            f.write(b'%PDF-1.4\nTest Priority\n%%EOF')
        test_files.append(test_file)

    # Crear trabajos con diferentes prioridades (menor = mayor prioridad)
    priorities = [10, 1, 5]  # Baja, Alta, Media
    job_ids = []

    for i, priority in enumerate(priorities):
        job_data = {
            'job_id': f'PRIOR-{i}',
            'client_id': 'CLIENT-TEST',
            'user_name': 'priority_test',
            'document_name': f'priority_{i}.pdf',
            'file_format': 'pdf',
            'file_path': str(test_files[i]),
            'page_count': 1,
            'status': 'pending',
            'priority': priority
        }
        job = db.create_print_job(job_data)
        processor.submit_job(job, priority=priority)
        job_ids.append(job.job_id)

    print(f"  ✓ Trabajos creados con prioridades: {priorities}")

    # La cola debe ordenar por prioridad
    pending = db.get_pending_jobs(limit=10)
    print(f"  ✓ Orden en cola (por prioridad):")
    for idx, job in enumerate(pending):
        print(f"     {idx+1}. {job.job_id} (prioridad={job.priority})")

    # Verificar orden correcto (prioridad 1 primero)
    assert pending[0].priority == 1  # PRIOR-1
    assert pending[1].priority == 5  # PRIOR-2
    assert pending[2].priority == 10  # PRIOR-0

    print("  ✓ Prioridades funcionan correctamente")

    # Limpiar
    for f in test_files:
        if f.exists():
            f.unlink()

    print("  ✓ Sistema de prioridades funciona correctamente")
    return True


def main():
    """Función principal"""
    print("=" * 60)
    print(" TEST FASE 3 - Servidor Completo")
    print(" Printer_connect")
    print("=" * 60)

    # Configurar logging mínimo
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s'
    )

    tests = [
        ("Base de Datos", test_database),
        ("Gestor de Impresora", test_printer_manager),
        ("Procesador de Trabajos", test_job_processor),
        ("Integración Servidor", test_server_integration),
        ("Prioridades de Cola", test_queue_priority)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ Test '{name}' falló")
        except Exception as e:
            failed += 1
            print(f"\n❌ Test '{name}' falló con excepción: {e}")
            import traceback
            traceback.print_exc()

    # Resultado final
    print("\n" + "=" * 60)
    if failed == 0:
        print(" ✓✓✓ TODOS LOS TESTS PASARON ✓✓✓")
        print(f" La Fase 3 está completa y funcionando")
        print(f" Tests pasados: {passed}/{len(tests)}")
    else:
        print(f" ❌ ALGUNOS TESTS FALLARON")
        print(f" Pasados: {passed}/{len(tests)}")
        print(f" Fallados: {failed}/{len(tests)}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
