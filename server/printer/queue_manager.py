"""
Gestor de cola de impresión con prioridades
"""

import logging
import threading
import time
from typing import Optional, List, Callable
from queue import PriorityQueue, Empty
from dataclasses import dataclass, field
from datetime import datetime

from server.database.database import Database
from server.database.models import PrintJob


@dataclass(order=True)
class QueueItem:
    """Item de la cola con prioridad"""
    priority: int
    timestamp: datetime = field(compare=False)
    job_id: str = field(compare=False)
    job_data: dict = field(compare=False)

    def __repr__(self):
        return f"QueueItem(priority={self.priority}, job_id={self.job_id})"


class PrintQueueManager:
    """Gestor de cola de impresión"""

    def __init__(
        self,
        database: Database,
        processor_callback: Optional[Callable] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el gestor de cola

        Args:
            database: Instancia de base de datos
            processor_callback: Función que procesa los trabajos
            logger: Logger para mensajes
        """
        self.database = database
        self.processor_callback = processor_callback
        self.logger = logger or logging.getLogger(__name__)

        # Cola de prioridad (menor número = mayor prioridad)
        self.queue = PriorityQueue()

        # Control de procesamiento
        self.processing = False
        self.processor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Estadísticas
        self.jobs_processed = 0
        self.jobs_failed = 0

        self.logger.info("Gestor de cola de impresión inicializado")

    def add_job(
        self,
        job_id: str,
        priority: int = 5,
        job_data: Optional[dict] = None
    ):
        """
        Agrega un trabajo a la cola

        Args:
            job_id: ID del trabajo
            priority: Prioridad (1=alta, 10=baja)
            job_data: Datos adicionales del trabajo
        """
        item = QueueItem(
            priority=priority,
            timestamp=datetime.now(),
            job_id=job_id,
            job_data=job_data or {}
        )

        self.queue.put(item)
        self.logger.info(
            f"Trabajo agregado a la cola: {job_id} "
            f"(prioridad={priority}, tamaño cola={self.queue.qsize()})"
        )

        # Actualizar posición en cola en BD
        self._update_queue_positions()

    def start_processing(self):
        """Inicia el procesamiento de la cola"""
        if self.processing:
            self.logger.warning("El procesamiento ya está en marcha")
            return

        self.processing = True
        self.stop_event.clear()

        self.processor_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.processor_thread.start()

        self.logger.info("Procesamiento de cola iniciado")

    def stop_processing(self):
        """Detiene el procesamiento de la cola"""
        if not self.processing:
            return

        self.logger.info("Deteniendo procesamiento de cola...")
        self.stop_event.set()
        self.processing = False

        if self.processor_thread:
            self.processor_thread.join(timeout=5)

        self.logger.info("Procesamiento de cola detenido")

    def _process_queue(self):
        """Loop principal de procesamiento de cola"""
        self.logger.info("Loop de procesamiento iniciado")

        while not self.stop_event.is_set():
            try:
                # Intentar obtener item con timeout
                try:
                    item = self.queue.get(timeout=1)
                except Empty:
                    continue

                self.logger.info(
                    f"Procesando trabajo: {item.job_id} "
                    f"(prioridad={item.priority})"
                )

                # Actualizar estado en BD
                self.database.update_print_job(
                    item.job_id,
                    {
                        'status': 'printing',
                        'started_at': datetime.utcnow()
                    }
                )

                # Procesar trabajo
                success = self._process_job(item)

                # Actualizar estado final
                if success:
                    self.database.update_print_job(
                        item.job_id,
                        {
                            'status': 'completed',
                            'completed_at': datetime.utcnow()
                        }
                    )
                    self.jobs_processed += 1
                    self.logger.info(f"Trabajo completado: {item.job_id}")
                else:
                    # Manejar fallo
                    job = self.database.get_print_job(item.job_id)
                    if job and job.retry_count < job.max_retries:
                        # Reintentar
                        self.database.update_print_job(
                            item.job_id,
                            {
                                'status': 'pending',
                                'retry_count': job.retry_count + 1
                            }
                        )
                        self.add_job(
                            item.job_id,
                            priority=item.priority + 1,  # Menor prioridad
                            job_data=item.job_data
                        )
                        self.logger.warning(
                            f"Trabajo reintentado: {item.job_id} "
                            f"({job.retry_count + 1}/{job.max_retries})"
                        )
                    else:
                        # Marcar como fallido
                        self.database.update_print_job(
                            item.job_id,
                            {
                                'status': 'failed',
                                'completed_at': datetime.utcnow()
                            }
                        )
                        self.jobs_failed += 1
                        self.logger.error(f"Trabajo fallido: {item.job_id}")

                # Marcar como procesado en cola
                self.queue.task_done()

                # Actualizar posiciones
                self._update_queue_positions()

            except Exception as e:
                self.logger.error(
                    f"Error procesando trabajo: {e}",
                    exc_info=True
                )

        self.logger.info("Loop de procesamiento finalizado")

    def _process_job(self, item: QueueItem) -> bool:
        """
        Procesa un trabajo de impresión

        Args:
            item: Item de la cola

        Returns:
            True si se procesó correctamente
        """
        if self.processor_callback:
            try:
                # Obtener trabajo completo de BD
                job = self.database.get_print_job(item.job_id)
                if not job:
                    self.logger.error(f"Trabajo no encontrado en BD: {item.job_id}")
                    return False

                # Llamar al callback de procesamiento
                result = self.processor_callback(job)
                return result

            except Exception as e:
                self.logger.error(
                    f"Error en callback de procesamiento: {e}",
                    exc_info=True
                )
                return False
        else:
            # Sin callback, simular procesamiento
            self.logger.warning(
                "No hay callback de procesamiento, simulando..."
            )
            time.sleep(1)
            return True

    def _update_queue_positions(self):
        """Actualiza las posiciones en cola en la base de datos"""
        try:
            # Obtener todos los items de la cola (sin consumirlos)
            items = []
            temp_queue = PriorityQueue()

            while not self.queue.empty():
                try:
                    item = self.queue.get_nowait()
                    items.append(item)
                    temp_queue.put(item)
                except Empty:
                    break

            # Restaurar cola
            self.queue = temp_queue

            # Actualizar posiciones en BD
            for position, item in enumerate(items, start=1):
                self.database.update_print_job(
                    item.job_id,
                    {'queue_position': position}
                )

        except Exception as e:
            self.logger.error(f"Error actualizando posiciones: {e}")

    def get_queue_size(self) -> int:
        """Retorna el tamaño actual de la cola"""
        return self.queue.qsize()

    def get_queue_status(self) -> dict:
        """Retorna el estado de la cola"""
        return {
            'queue_size': self.queue.qsize(),
            'processing': self.processing,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed
        }

    def clear_queue(self):
        """Limpia la cola (útil para tests)"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Empty:
                break

        self.logger.info("Cola limpiada")

    def load_pending_jobs(self):
        """Carga trabajos pendientes de la BD a la cola"""
        self.logger.info("Cargando trabajos pendientes de la BD...")

        pending_jobs = self.database.get_pending_jobs(limit=1000)

        for job in pending_jobs:
            self.add_job(
                job_id=job.job_id,
                priority=job.priority,
                job_data={'file_path': job.file_path}
            )

        self.logger.info(f"Cargados {len(pending_jobs)} trabajos pendientes")
