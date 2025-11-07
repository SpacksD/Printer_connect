"""
Gestor de impresora física
Abstracción para diferentes plataformas (Windows/Linux)
"""

import logging
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod


class PrinterInterface(ABC):
    """Interfaz abstracta para gestores de impresora"""

    @abstractmethod
    def get_printers(self) -> List[str]:
        """Obtiene lista de impresoras disponibles"""
        pass

    @abstractmethod
    def print_file(
        self,
        printer_name: str,
        file_path: Path,
        **kwargs
    ) -> bool:
        """Imprime un archivo"""
        pass

    @abstractmethod
    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Obtiene el estado de la impresora"""
        pass


class WindowsPrinterManager(PrinterInterface):
    """Gestor de impresora para Windows usando win32print"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        try:
            import win32print
            import win32api
            self.win32print = win32print
            self.win32api = win32api
            self.available = True
            self.logger.info("win32print disponible")
        except ImportError:
            self.available = False
            self.logger.warning(
                "win32print no disponible. "
                "Instala pywin32: pip install pywin32"
            )

    def get_printers(self) -> List[str]:
        """Obtiene lista de impresoras disponibles"""
        if not self.available:
            return []

        try:
            printers = []
            printer_enum = self.win32print.EnumPrinters(
                self.win32print.PRINTER_ENUM_LOCAL | self.win32print.PRINTER_ENUM_CONNECTIONS
            )

            for printer_info in printer_enum:
                printers.append(printer_info[2])  # Nombre de impresora

            return printers

        except Exception as e:
            self.logger.error(f"Error obteniendo impresoras: {e}")
            return []

    def print_file(
        self,
        printer_name: str,
        file_path: Path,
        **kwargs
    ) -> bool:
        """
        Imprime un archivo PDF

        Args:
            printer_name: Nombre de la impresora
            file_path: Ruta al archivo PDF
            **kwargs: Parámetros adicionales (copies, etc.)

        Returns:
            True si se imprimió correctamente
        """
        if not self.available:
            self.logger.error("win32print no está disponible")
            return False

        if not file_path.exists():
            self.logger.error(f"Archivo no encontrado: {file_path}")
            return False

        try:
            # Usar ShellExecute para imprimir (más simple y universal)
            self.win32api.ShellExecute(
                0,
                "printto",
                str(file_path),
                f'"{printer_name}"',
                ".",
                0
            )

            self.logger.info(f"Archivo enviado a impresora: {file_path} → {printer_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error imprimiendo archivo: {e}", exc_info=True)
            return False

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Obtiene el estado de la impresora"""
        if not self.available:
            return {'status': 'unknown', 'available': False}

        try:
            handle = self.win32print.OpenPrinter(printer_name)

            try:
                printer_info = self.win32print.GetPrinter(handle, 2)

                status_flags = printer_info['Status']

                # Decodificar flags de estado
                statuses = []
                if status_flags == 0:
                    statuses.append('ready')
                if status_flags & self.win32print.PRINTER_STATUS_PAUSED:
                    statuses.append('paused')
                if status_flags & self.win32print.PRINTER_STATUS_ERROR:
                    statuses.append('error')
                if status_flags & self.win32print.PRINTER_STATUS_PENDING_DELETION:
                    statuses.append('pending_deletion')
                if status_flags & self.win32print.PRINTER_STATUS_PAPER_JAM:
                    statuses.append('paper_jam')
                if status_flags & self.win32print.PRINTER_STATUS_PAPER_OUT:
                    statuses.append('paper_out')
                if status_flags & self.win32print.PRINTER_STATUS_OFFLINE:
                    statuses.append('offline')
                if status_flags & self.win32print.PRINTER_STATUS_PRINTING:
                    statuses.append('printing')

                return {
                    'status': statuses[0] if statuses else 'ready',
                    'all_statuses': statuses,
                    'available': True,
                    'jobs_count': printer_info['cJobs']
                }

            finally:
                self.win32print.ClosePrinter(handle)

        except Exception as e:
            self.logger.error(f"Error obteniendo estado de impresora: {e}")
            return {'status': 'error', 'available': False, 'error': str(e)}


class CUPSPrinterManager(PrinterInterface):
    """Gestor de impresora para Linux usando CUPS"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        try:
            import cups
            self.cups = cups
            self.connection = cups.Connection()
            self.available = True
            self.logger.info("CUPS disponible")
        except ImportError:
            self.available = False
            self.logger.warning(
                "pycups no disponible. "
                "Instala: pip install pycups"
            )

    def get_printers(self) -> List[str]:
        """Obtiene lista de impresoras disponibles"""
        if not self.available:
            return []

        try:
            printers = self.connection.getPrinters()
            return list(printers.keys())
        except Exception as e:
            self.logger.error(f"Error obteniendo impresoras: {e}")
            return []

    def print_file(
        self,
        printer_name: str,
        file_path: Path,
        **kwargs
    ) -> bool:
        """Imprime un archivo"""
        if not self.available:
            self.logger.error("CUPS no está disponible")
            return False

        if not file_path.exists():
            self.logger.error(f"Archivo no encontrado: {file_path}")
            return False

        try:
            job_id = self.connection.printFile(
                printer_name,
                str(file_path),
                file_path.name,
                {}
            )

            self.logger.info(
                f"Archivo enviado a impresora: {file_path} → {printer_name} "
                f"(Job ID: {job_id})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error imprimiendo archivo: {e}", exc_info=True)
            return False

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Obtiene el estado de la impresora"""
        if not self.available:
            return {'status': 'unknown', 'available': False}

        try:
            printers = self.connection.getPrinters()

            if printer_name not in printers:
                return {'status': 'not_found', 'available': False}

            printer_info = printers[printer_name]

            return {
                'status': printer_info['printer-state-message'],
                'available': printer_info['printer-is-accepting-jobs'],
                'state': printer_info['printer-state']
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo estado: {e}")
            return {'status': 'error', 'available': False, 'error': str(e)}


class MockPrinterManager(PrinterInterface):
    """Gestor mock para testing"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.printed_files: List[Path] = []
        self.available = True
        self.logger.info("Mock printer manager inicializado")

    def get_printers(self) -> List[str]:
        """Obtiene lista de impresoras mock"""
        return ["Mock Printer 1", "Mock Printer 2"]

    def print_file(
        self,
        printer_name: str,
        file_path: Path,
        **kwargs
    ) -> bool:
        """Simula impresión de archivo"""
        if not file_path.exists():
            self.logger.error(f"Archivo no encontrado: {file_path}")
            return False

        self.printed_files.append(file_path)
        self.logger.info(f"[MOCK] Archivo 'impreso': {file_path} → {printer_name}")
        return True

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Obtiene estado mock"""
        return {
            'status': 'ready',
            'available': True,
            'jobs_count': 0
        }

    def get_printed_files(self) -> List[Path]:
        """Obtiene lista de archivos 'impresos'"""
        return self.printed_files.copy()


class PrinterManager:
    """
    Gestor principal de impresora
    Selecciona automáticamente el backend apropiado
    """

    def __init__(
        self,
        printer_name: Optional[str] = None,
        use_mock: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el gestor de impresora

        Args:
            printer_name: Nombre de la impresora a usar
            use_mock: Usar mock en lugar de impresora real
            logger: Logger para mensajes
        """
        self.logger = logger or logging.getLogger(__name__)
        self.printer_name = printer_name

        # Seleccionar backend
        if use_mock:
            self.backend = MockPrinterManager(logger=self.logger)
            self.logger.info("Usando MockPrinterManager")
        else:
            system = platform.system()

            if system == 'Windows':
                self.backend = WindowsPrinterManager(logger=self.logger)
                self.logger.info("Usando WindowsPrinterManager")
            elif system == 'Linux':
                self.backend = CUPSPrinterManager(logger=self.logger)
                self.logger.info("Usando CUPSPrinterManager")
            else:
                self.logger.warning(
                    f"Sistema no soportado: {system}. Usando Mock."
                )
                self.backend = MockPrinterManager(logger=self.logger)

        # Verificar si el backend está disponible
        if not self.backend.available:
            self.logger.warning("Backend no disponible, usando Mock")
            self.backend = MockPrinterManager(logger=self.logger)

    def get_printers(self) -> List[str]:
        """Obtiene lista de impresoras disponibles"""
        return self.backend.get_printers()

    def print_file(self, file_path: Path, **kwargs) -> bool:
        """
        Imprime un archivo en la impresora configurada

        Args:
            file_path: Ruta al archivo a imprimir
            **kwargs: Parámetros adicionales

        Returns:
            True si se imprimió correctamente
        """
        if not self.printer_name:
            # Usar impresora por defecto (primera disponible)
            printers = self.get_printers()
            if not printers:
                self.logger.error("No hay impresoras disponibles")
                return False

            self.printer_name = printers[0]
            self.logger.info(f"Usando impresora por defecto: {self.printer_name}")

        return self.backend.print_file(self.printer_name, file_path, **kwargs)

    def get_printer_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la impresora configurada"""
        if not self.printer_name:
            return {'status': 'not_configured', 'available': False}

        return self.backend.get_printer_status(self.printer_name)

    def set_printer(self, printer_name: str):
        """Establece la impresora a usar"""
        printers = self.get_printers()

        if printer_name not in printers:
            self.logger.warning(
                f"Impresora '{printer_name}' no encontrada. "
                f"Disponibles: {printers}"
            )

        self.printer_name = printer_name
        self.logger.info(f"Impresora establecida: {printer_name}")
