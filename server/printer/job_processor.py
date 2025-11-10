"""
Procesador de trabajos de impresión
Une la cola, la base de datos y el gestor de impresora
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from server.database.database import Database
from server.database.models import PrintJob
from server.printer.printer_manager import PrinterManager
from server.printer.queue_manager import PrintQueueManager


class JobProcessor:
    """Procesador de trabajos de impresión"""

    def __init__(
        self,
        database: Database,
        printer_manager: PrinterManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el procesador

        Args:
            database: Instancia de base de datos
            printer_manager: Gestor de impresora
            logger: Logger para mensajes
        """
        self.database = database
        self.printer_manager = printer_manager
        self.logger = logger or logging.getLogger(__name__)

        # Crear gestor de cola
        self.queue_manager = PrintQueueManager(
            database=database,
            processor_callback=self.process_job,
            logger=logger
        )

        self.logger.info("Procesador de trabajos inicializado")

    def submit_job(self, job: PrintJob, priority: Optional[int] = None):
        """
        Envía un trabajo a la cola

        Args:
            job: Trabajo de impresión
            priority: Prioridad opcional (sobrescribe la del trabajo)
        """
        job_priority = priority or job.priority or 5

        self.queue_manager.add_job(
            job_id=job.job_id,
            priority=job_priority,
            job_data={'file_path': job.file_path}
        )

        self.logger.info(
            f"Trabajo enviado a cola: {job.job_id} "
            f"(prioridad={job_priority})"
        )

    def process_job(self, job: PrintJob) -> bool:
        """
        Procesa un trabajo de impresión

        Args:
            job: Trabajo a procesar

        Returns:
            True si se procesó correctamente
        """
        self.logger.info(f"Procesando trabajo: {job.job_id}")

        try:
            # Verificar que el archivo existe
            file_path = Path(job.file_path)

            if not file_path.exists():
                error_msg = f"Archivo no encontrado: {file_path}"
                self.logger.error(error_msg)

                self.database.update_print_job(
                    job.job_id,
                    {'error_message': error_msg}
                )
                return False

            # Verificar estado de impresora
            printer_status = self.printer_manager.get_printer_status()

            if not printer_status.get('available', False):
                error_msg = f"Impresora no disponible: {printer_status.get('status')}"
                self.logger.warning(error_msg)

                # No marcar como fallido, solo reintentará
                self.database.update_print_job(
                    job.job_id,
                    {'error_message': error_msg}
                )
                return False

            # Registrar inicio
            start_time = datetime.now()

            # Enviar a impresora
            self.logger.info(
                f"Enviando a impresora: {file_path} "
                f"(usuario={job.user_name}, páginas={job.page_count})"
            )

            success = self.printer_manager.print_file(
                file_path,
                copies=job.copies or 1
            )

            # Calcular tiempo de procesamiento
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if success:
                self.logger.info(
                    f"Trabajo impreso exitosamente: {job.job_id} "
                    f"({processing_time_ms}ms)"
                )

                # Actualizar estadísticas
                self.database.update_print_job(
                    job.job_id,
                    {
                        'processing_time_ms': processing_time_ms,
                        'error_message': None
                    }
                )

                # Actualizar estadísticas del cliente
                self.database.increment_client_stats(
                    job.client_id,
                    jobs=1,
                    pages=job.page_count or 0
                )

                return True

            else:
                error_msg = "Error al imprimir archivo"
                self.logger.error(f"{error_msg}: {job.job_id}")

                self.database.update_print_job(
                    job.job_id,
                    {
                        'error_message': error_msg,
                        'processing_time_ms': processing_time_ms
                    }
                )

                return False

        except Exception as e:
            error_msg = f"Excepción procesando trabajo: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            self.database.update_print_job(
                job.job_id,
                {'error_message': error_msg}
            )

            return False

    def start(self):
        """Inicia el procesamiento de la cola"""
        self.logger.info("Iniciando procesador de trabajos...")

        # Cargar trabajos pendientes de la BD
        self.queue_manager.load_pending_jobs()

        # Iniciar procesamiento
        self.queue_manager.start_processing()

        self.logger.info("Procesador de trabajos iniciado")

    def stop(self):
        """Detiene el procesamiento"""
        self.logger.info("Deteniendo procesador de trabajos...")
        self.queue_manager.stop_processing()
        self.logger.info("Procesador detenido")

    def get_status(self) -> dict:
        """Obtiene el estado del procesador"""
        queue_status = self.queue_manager.get_queue_status()
        printer_status = self.printer_manager.get_printer_status()
        db_summary = self.database.get_summary()

        return {
            'queue': queue_status,
            'printer': printer_status,
            'database': db_summary
        }
