#!/usr/bin/env python3
"""
Script de prueba end-to-end para la Fase 2
Simula el flujo completo de la impresora virtual
"""

import sys
import time
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from client.printer_driver.converter import MockConverter, parse_postscript_params
from client.printer_driver.print_monitor import PrintJobHandler
from client.network.client import PrintClient
from server.network.server import PrintServer
import threading
import logging


def create_test_postscript(output_file: Path):
    """Crea un archivo PostScript de prueba"""
    content = """
%!PS-Adobe-3.0
%%Title: Test Document for Phase 2
%%Creator: Printer_connect Test Suite
%%Pages: 2
%%BoundingBox: 0 0 612 792
%%Orientation: Portrait
%%EndComments

%%Page: 1 1
/Times-Roman findfont 24 scalefont setfont
100 700 moveto
(This is page 1) show
showpage

%%Page: 2 2
/Times-Roman findfont 24 scalefont setfont
100 700 moveto
(This is page 2) show
showpage

%%EOF
"""
    with open(output_file, 'w') as f:
        f.write(content)


def test_postscript_parser():
    """Test del parser de PostScript"""
    print("\n[TEST] Probando parser de PostScript...")

    test_dir = Path('./test_phase2_temp')
    test_dir.mkdir(exist_ok=True)

    ps_file = test_dir / 'test.ps'
    create_test_postscript(ps_file)

    params = parse_postscript_params(ps_file)

    print(f"  Título: {params.get('title')}")
    print(f"  Creador: {params.get('creator')}")
    print(f"  Páginas: {params.get('pages')}")
    print(f"  Tamaño: {params.get('page_size')}")
    print(f"  Orientación: {params.get('orientation')}")

    assert params['title'] == 'Test Document for Phase 2'
    assert params['creator'] == 'Printer_connect Test Suite'
    assert params['pages'] == 2
    assert params['page_size'] == 'Letter'
    assert params['orientation'] == 'portrait'

    print("  ✓ Parser funciona correctamente")

    # Limpiar
    ps_file.unlink()

    return True


def test_converter():
    """Test del conversor de formatos"""
    print("\n[TEST] Probando conversor de formatos...")

    test_dir = Path('./test_phase2_temp')
    test_dir.mkdir(exist_ok=True)

    ps_file = test_dir / 'test.ps'
    pdf_file = test_dir / 'test.pdf'

    create_test_postscript(ps_file)

    # Usar mock converter para testing sin GhostScript
    converter = MockConverter()

    print("  Convirtiendo PostScript a PDF...")
    result = converter.postscript_to_pdf(ps_file, pdf_file)

    assert result is True
    assert pdf_file.exists()

    print(f"  ✓ Conversión exitosa: {pdf_file}")
    print(f"  Tamaño del PDF: {pdf_file.stat().st_size} bytes")

    # Extraer número de páginas
    page_count = converter.extract_page_count(pdf_file)
    print(f"  Número de páginas: {page_count}")

    # Limpiar
    ps_file.unlink()
    pdf_file.unlink()

    print("  ✓ Conversor funciona correctamente")

    return True


def test_print_job_flow():
    """Test del flujo completo de trabajo de impresión"""
    print("\n[TEST] Probando flujo completo...")

    test_dir = Path('./test_phase2_temp')
    test_dir.mkdir(exist_ok=True)

    # 1. Crear PostScript
    print("  [1/5] Creando trabajo de impresión...")
    ps_file = test_dir / 'job.ps'
    create_test_postscript(ps_file)

    # 2. Parsear parámetros
    print("  [2/5] Extrayendo parámetros...")
    ps_params = parse_postscript_params(ps_file)

    # 3. Convertir a PDF
    print("  [3/5] Convirtiendo a PDF...")
    pdf_file = test_dir / 'job.pdf'
    converter = MockConverter()
    converter.postscript_to_pdf(ps_file, pdf_file)

    # 4. Crear metadata
    print("  [4/5] Creando metadata...")
    metadata = {
        'job_id': 'TEST-JOB-001',
        'timestamp': '2025-11-07T12:00:00',
        'user': 'test_user',
        'pdf_file': str(pdf_file),
        'pdf_size': pdf_file.stat().st_size,
        'page_count': converter.extract_page_count(pdf_file),
        'ps_params': ps_params,
        'status': 'ready_to_send'
    }

    metadata_file = test_dir / 'job.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✓ Metadata guardada: {metadata_file}")

    # 5. Verificar archivos
    print("  [5/5] Verificando archivos creados...")
    assert ps_file.exists()
    assert pdf_file.exists()
    assert metadata_file.exists()

    print("  ✓ Todos los archivos creados correctamente")

    # Mostrar resumen
    print("\n  Resumen del trabajo:")
    print(f"    Job ID: {metadata['job_id']}")
    print(f"    Usuario: {metadata['user']}")
    print(f"    Páginas: {metadata['page_count']}")
    print(f"    PDF: {metadata['pdf_size']} bytes")

    # Limpiar
    ps_file.unlink()
    pdf_file.unlink()
    metadata_file.unlink()

    print("\n  ✓ Flujo completo funciona correctamente")

    return True


def main():
    """Función principal"""
    print("=" * 60)
    print(" TEST FASE 2 - Impresora Virtual")
    print(" Printer_connect")
    print("=" * 60)

    try:
        # Test 1: Parser
        if not test_postscript_parser():
            print("\n❌ Test del parser falló")
            return 1

        # Test 2: Converter
        if not test_converter():
            print("\n❌ Test del conversor falló")
            return 1

        # Test 3: Flujo completo
        if not test_print_job_flow():
            print("\n❌ Test del flujo completo falló")
            return 1

        # Limpiar
        test_dir = Path('./test_phase2_temp')
        if test_dir.exists():
            test_dir.rmdir()

        # Éxito
        print("\n" + "=" * 60)
        print(" ✓✓✓ TODAS LAS PRUEBAS PASARON ✓✓✓")
        print(" La Fase 2 está completa y funcionando")
        print("=" * 60)
        print()
        print("Nota: Estas pruebas usan un conversor mock.")
        print("Para pruebas reales en Windows, necesitas:")
        print("  - GhostScript instalado")
        print("  - RedMon instalado")
        print("  - Impresora virtual configurada")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
