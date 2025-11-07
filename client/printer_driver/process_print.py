"""
Script ejecutado por RedMon cuando se recibe un trabajo de impresión
Este script es llamado por el Port Monitor de Windows

Uso:
    process_print.py < input.ps > output.log

El trabajo de impresión (PostScript) se recibe por stdin
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import os

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.printer_driver.converter import FormatConverter, parse_postscript_params
from client.utils.logger import setup_logger


def main():
    """Función principal del script"""

    # Setup de logging
    log_dir = Path(os.getenv('PRINTER_CONNECT_LOG_DIR', './logs'))
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger(
        log_file=log_dir / 'print_processor.log',
        log_level='INFO'
    )

    logger.info("=" * 60)
    logger.info("Procesador de trabajos de impresión iniciado")
    logger.info("=" * 60)

    try:
        # Leer PostScript desde stdin
        logger.info("Leyendo trabajo de impresión desde stdin...")
        ps_data = sys.stdin.buffer.read()

        if not ps_data:
            logger.error("No se recibieron datos desde stdin")
            sys.exit(1)

        logger.info(f"Recibidos {len(ps_data)} bytes de datos PostScript")

        # Crear carpeta de salida
        output_dir = Path(os.getenv('PRINTER_CONNECT_OUTPUT_DIR', './print_jobs'))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generar nombre de archivo único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        job_id = f"PRINT_{timestamp}"

        temp_ps = output_dir / f"{job_id}.ps"
        output_pdf = output_dir / f"{job_id}.pdf"
        metadata_file = output_dir / f"{job_id}.json"

        # Guardar PostScript temporalmente
        with open(temp_ps, 'wb') as f:
            f.write(ps_data)

        logger.info(f"PostScript guardado en: {temp_ps}")

        # Parsear parámetros del PostScript
        logger.info("Extrayendo parámetros del PostScript...")
        ps_params = parse_postscript_params(temp_ps)
        logger.info(f"Parámetros extraídos: {ps_params}")

        # Convertir a PDF
        logger.info("Convirtiendo PostScript a PDF...")
        converter = FormatConverter(logger=logger)

        if not converter.is_available():
            logger.error("GhostScript no está disponible")
            logger.error("Asegúrate de que GhostScript esté instalado y en el PATH")
            sys.exit(1)

        success = converter.postscript_to_pdf(temp_ps, output_pdf)

        if not success:
            logger.error("Error en la conversión a PDF")
            sys.exit(1)

        logger.info(f"PDF generado exitosamente: {output_pdf}")

        # Contar páginas
        page_count = converter.extract_page_count(output_pdf)
        logger.info(f"Número de páginas: {page_count}")

        # Obtener información del usuario y proceso
        user = os.getenv('USERNAME', 'unknown')

        # Crear metadata
        metadata = {
            'job_id': job_id,
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'pdf_file': str(output_pdf),
            'pdf_size': output_pdf.stat().st_size,
            'page_count': page_count,
            'ps_params': ps_params,
            'status': 'ready_to_send'
        }

        # Guardar metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata guardada en: {metadata_file}")

        # Limpiar archivo PostScript temporal
        temp_ps.unlink()
        logger.info("Archivo PostScript temporal eliminado")

        logger.info("=" * 60)
        logger.info("Trabajo de impresión procesado exitosamente")
        logger.info(f"Job ID: {job_id}")
        logger.info(f"PDF: {output_pdf}")
        logger.info("=" * 60)

        # Éxito
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
