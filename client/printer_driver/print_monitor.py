"""
Monitor de trabajos de impresión
Detecta nuevos PDFs generados por process_print.py y los envía al servidor
"""

import sys
import time
import json
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

# Para monitoreo de archivos, intentar usar watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Crear clase dummy si watchdog no está disponible
    class FileSystemEventHandler:
        """Clase base dummy si watchdog no está disponible"""
        pass

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.network.client import PrintClient
from client.utils.config import ConfigManager
from shared.data_models import PrintParameters, PrintJobMetadata


class PrintJobHandler(FileSystemEventHandler):
    """Manejador de eventos de archivos para trabajos de impresión"""

    def __init__(
        self,
        client: PrintClient,
        client_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el manejador

        Args:
            client: Cliente para envío al servidor
            client_id: ID del cliente
            logger: Logger para mensajes
        """
        self.client = client
        self.client_id = client_id
        self.logger = logger or logging.getLogger(__name__)

    def on_created(self, event):
        """
        Maneja eventos de creación de archivos

        Args:
            event: Evento de creación
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Solo procesar archivos JSON (metadata)
        if file_path.suffix != '.json':
            return

        self.logger.info(f"Nuevo trabajo detectado: {file_path}")

        # Esperar un momento para asegurar que el archivo esté completo
        time.sleep(0.5)

        try:
            self._process_print_job(file_path)
        except Exception as e:
            self.logger.error(f"Error procesando trabajo: {e}", exc_info=True)

    def _process_print_job(self, metadata_file: Path):
        """
        Procesa un trabajo de impresión

        Args:
            metadata_file: Archivo JSON con metadata del trabajo
        """
        # Leer metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Verificar estado
        if metadata.get('status') != 'ready_to_send':
            self.logger.warning(f"Trabajo no está listo: {metadata.get('status')}")
            return

        pdf_file = Path(metadata['pdf_file'])

        if not pdf_file.exists():
            self.logger.error(f"Archivo PDF no encontrado: {pdf_file}")
            return

        self.logger.info(f"Procesando trabajo: {metadata['job_id']}")
        self.logger.info(f"Usuario: {metadata['user']}")
        self.logger.info(f"Páginas: {metadata['page_count']}")

        # Preparar parámetros de impresión
        ps_params = metadata.get('ps_params', {})

        parameters = PrintParameters(
            page_size=self._normalize_page_size(ps_params.get('page_size', 'A4')),
            orientation=self._normalize_orientation(ps_params.get('orientation', 'portrait'))
        )

        # Preparar metadata
        job_metadata = PrintJobMetadata(
            document_name=ps_params.get('title', pdf_file.name),
            page_count=metadata.get('page_count', 1),
            application=ps_params.get('creator', 'Unknown'),
            file_size_bytes=metadata.get('pdf_size', 0)
        )

        # Enviar al servidor
        try:
            self.logger.info("Enviando al servidor...")

            response = self.client.send_print_job(
                client_id=self.client_id,
                user=metadata['user'],
                file_path=pdf_file,
                parameters=parameters,
                metadata=job_metadata
            )

            if response['status'] == 'success':
                self.logger.info(f"Trabajo enviado exitosamente: {response.get('job_id')}")

                # Marcar como enviado
                metadata['status'] = 'sent'
                metadata['server_job_id'] = response.get('job_id')
                metadata['sent_at'] = datetime.now().isoformat()

                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

                # Opcional: mover a carpeta de completados
                completed_dir = pdf_file.parent / 'completed'
                completed_dir.mkdir(exist_ok=True)

                pdf_file.rename(completed_dir / pdf_file.name)
                metadata_file.rename(completed_dir / metadata_file.name)

                self.logger.info("Archivos movidos a carpeta 'completed'")

            else:
                self.logger.error(f"Error del servidor: {response.get('message')}")

                # Marcar como fallido
                metadata['status'] = 'failed'
                metadata['error'] = response.get('message')

                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error enviando al servidor: {e}", exc_info=True)

            # Marcar como fallido
            metadata['status'] = 'failed'
            metadata['error'] = str(e)

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

    def _normalize_page_size(self, page_size: str):
        """Normaliza el tamaño de página a los valores soportados"""
        from shared.data_models import PageSize

        page_size_upper = page_size.upper() if page_size else 'A4'

        try:
            return PageSize[page_size_upper]
        except KeyError:
            return PageSize.A4

    def _normalize_orientation(self, orientation: str):
        """Normaliza la orientación"""
        from shared.data_models import Orientation

        if orientation and orientation.lower() == 'landscape':
            return Orientation.LANDSCAPE
        else:
            return Orientation.PORTRAIT


class PrintMonitor:
    """Monitor de trabajos de impresión"""

    def __init__(
        self,
        watch_folder: Path,
        client: PrintClient,
        client_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el monitor

        Args:
            watch_folder: Carpeta a monitorear
            client: Cliente para envío
            client_id: ID del cliente
            logger: Logger
        """
        self.watch_folder = Path(watch_folder)
        self.client = client
        self.client_id = client_id
        self.logger = logger or logging.getLogger(__name__)
        self.observer = None

        # Crear carpeta si no existe
        self.watch_folder.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Inicia el monitoreo"""
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("watchdog no está disponible, usando polling")
            self._start_polling()
        else:
            self._start_watchdog()

    def _start_watchdog(self):
        """Inicia el monitoreo usando watchdog"""
        self.logger.info(f"Iniciando monitoreo de: {self.watch_folder}")

        event_handler = PrintJobHandler(
            client=self.client,
            client_id=self.client_id,
            logger=self.logger
        )

        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        self.observer.start()

        self.logger.info("Monitor iniciado exitosamente (watchdog)")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _start_polling(self):
        """Inicia el monitoreo usando polling"""
        self.logger.info(f"Iniciando monitoreo de: {self.watch_folder} (polling)")

        processed_files = set()

        try:
            while True:
                # Buscar archivos JSON nuevos
                for json_file in self.watch_folder.glob('*.json'):
                    if json_file in processed_files:
                        continue

                    # Procesar archivo
                    try:
                        handler = PrintJobHandler(
                            client=self.client,
                            client_id=self.client_id,
                            logger=self.logger
                        )
                        handler._process_print_job(json_file)
                        processed_files.add(json_file)

                    except Exception as e:
                        self.logger.error(f"Error procesando {json_file}: {e}")

                # Esperar antes del próximo ciclo
                time.sleep(2)

        except KeyboardInterrupt:
            self.logger.info("Monitor detenido por usuario")

    def stop(self):
        """Detiene el monitoreo"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Monitor detenido")


def main():
    """Función principal"""
    import os

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    print("=" * 60)
    print(" Printer_connect - Monitor de Impresión")
    print(" Versión 0.2.0")
    print("=" * 60)
    print()

    # Cargar configuración
    config_file = Path(__file__).parent.parent / 'config.ini'
    config = ConfigManager(config_file)

    # Obtener parámetros
    server_host, server_port = config.get_server_address()
    client_id = config.get('Client', 'client_id')
    watch_folder = Path(config.get('Client', 'temp_folder', './print_jobs'))

    print(f"Servidor: {server_host}:{server_port}")
    print(f"Client ID: {client_id}")
    print(f"Carpeta de monitoreo: {watch_folder}")
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
        print("❌ No se puede conectar al servidor")
        print(f"   Verifica que el servidor esté corriendo en {server_host}:{server_port}")
        sys.exit(1)

    print("✓ Conexión exitosa")
    print()
    print("-" * 60)
    print("Monitor iniciado. Esperando trabajos de impresión...")
    print("Presiona Ctrl+C para detener")
    print("-" * 60)
    print()

    # Crear y arrancar monitor
    monitor = PrintMonitor(
        watch_folder=watch_folder,
        client=client,
        client_id=client_id,
        logger=logger
    )

    monitor.start()


if __name__ == '__main__':
    main()
