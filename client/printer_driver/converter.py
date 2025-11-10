"""
Conversor de formatos de impresión a PDF
Utiliza GhostScript para la conversión
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging
import shutil


class FormatConverter:
    """Convierte diferentes formatos de impresión a PDF"""

    def __init__(
        self,
        ghostscript_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el conversor

        Args:
            ghostscript_path: Ruta al ejecutable de GhostScript
            logger: Logger para mensajes
        """
        self.logger = logger or logging.getLogger(__name__)

        # Buscar GhostScript
        if ghostscript_path and ghostscript_path.exists():
            self.gs_path = ghostscript_path
        else:
            self.gs_path = self._find_ghostscript()

        if self.gs_path:
            self.logger.info(f"GhostScript encontrado en: {self.gs_path}")
        else:
            self.logger.warning("GhostScript no encontrado")

    def _find_ghostscript(self) -> Optional[Path]:
        """
        Busca GhostScript en ubicaciones comunes

        Returns:
            Ruta al ejecutable de GhostScript o None
        """
        # Ubicaciones comunes en Windows
        possible_paths = [
            Path(r"C:\Program Files\gs\gs10.02.0\bin\gswin64c.exe"),
            Path(r"C:\Program Files\gs\gs10.01.0\bin\gswin64c.exe"),
            Path(r"C:\Program Files (x86)\gs\gs10.02.0\bin\gswin32c.exe"),
            Path(r"C:\Program Files (x86)\gs\gs10.01.0\bin\gswin32c.exe"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Intentar encontrar en PATH
        gs_command = shutil.which('gswin64c') or shutil.which('gswin32c') or shutil.which('gs')
        if gs_command:
            return Path(gs_command)

        return None

    def is_available(self) -> bool:
        """
        Verifica si el conversor está disponible

        Returns:
            True si GhostScript está disponible
        """
        return self.gs_path is not None and self.gs_path.exists()

    def postscript_to_pdf(
        self,
        ps_file: Path,
        pdf_file: Path,
        quality: str = 'printer'
    ) -> bool:
        """
        Convierte un archivo PostScript a PDF

        Args:
            ps_file: Archivo PostScript de entrada
            pdf_file: Archivo PDF de salida
            quality: Calidad de conversión (screen, ebook, printer, prepress)

        Returns:
            True si la conversión fue exitosa

        Raises:
            FileNotFoundError: Si el archivo PS no existe
            RuntimeError: Si GhostScript no está disponible
        """
        if not ps_file.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ps_file}")

        if not self.is_available():
            raise RuntimeError("GhostScript no está disponible")

        # Comando GhostScript
        command = [
            str(self.gs_path),
            '-dNOPAUSE',
            '-dBATCH',
            '-dSAFER',
            '-sDEVICE=pdfwrite',
            f'-dPDFSETTINGS=/{quality}',
            '-dColorConversionStrategy=/RGB',
            '-dAutoRotatePages=/None',
            f'-sOutputFile={pdf_file}',
            str(ps_file)
        ]

        self.logger.debug(f"Ejecutando: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )

            self.logger.info(f"Conversión exitosa: {ps_file} -> {pdf_file}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error en conversión: {e.stderr}")
            return False

    def stdin_to_pdf(
        self,
        stdin_data: bytes,
        pdf_file: Path,
        quality: str = 'printer'
    ) -> bool:
        """
        Convierte PostScript desde stdin a PDF

        Args:
            stdin_data: Datos PostScript en bytes
            pdf_file: Archivo PDF de salida
            quality: Calidad de conversión

        Returns:
            True si la conversión fue exitosa
        """
        if not self.is_available():
            raise RuntimeError("GhostScript no está disponible")

        # Guardar stdin a archivo temporal
        temp_ps = pdf_file.parent / f"{pdf_file.stem}_temp.ps"

        try:
            with open(temp_ps, 'wb') as f:
                f.write(stdin_data)

            result = self.postscript_to_pdf(temp_ps, pdf_file, quality)

            # Limpiar archivo temporal
            if temp_ps.exists():
                temp_ps.unlink()

            return result

        except Exception as e:
            self.logger.error(f"Error convirtiendo desde stdin: {e}")
            if temp_ps.exists():
                temp_ps.unlink()
            return False

    def extract_page_count(self, pdf_file: Path) -> int:
        """
        Extrae el número de páginas de un PDF

        Args:
            pdf_file: Archivo PDF

        Returns:
            Número de páginas
        """
        if not pdf_file.exists():
            return 0

        try:
            # Usar GhostScript para contar páginas
            command = [
                str(self.gs_path),
                '-dNODISPLAY',
                '-dQUIET',
                '-c',
                f'({pdf_file}) (r) file runpdfbegin pdfpagecount = quit'
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )

            page_count = int(result.stdout.strip())
            return page_count

        except Exception as e:
            self.logger.error(f"Error extrayendo número de páginas: {e}")
            return 0


def parse_postscript_params(ps_file: Path) -> dict:
    """
    Parsea parámetros desde comentarios DSC de PostScript

    Args:
        ps_file: Archivo PostScript

    Returns:
        Diccionario con parámetros extraídos
    """
    params = {
        'page_size': None,
        'orientation': None,
        'title': None,
        'creator': None,
        'pages': 0
    }

    try:
        with open(ps_file, 'rb') as f:
            # Leer solo las primeras 8KB (header)
            header = f.read(8192).decode('latin-1', errors='ignore')

            for line in header.split('\n'):
                if line.startswith('%%BoundingBox:'):
                    # Extraer tamaño de página
                    parts = line.split()
                    if len(parts) >= 5:
                        width = int(parts[3])
                        height = int(parts[4])

                        # Determinar tamaño de página
                        if width == 612 and height == 792:
                            params['page_size'] = 'Letter'
                        elif width == 595 and height == 842:
                            params['page_size'] = 'A4'
                        else:
                            params['page_size'] = f'{width}x{height}'

                elif line.startswith('%%Orientation:'):
                    orientation = line.split(':')[1].strip()
                    params['orientation'] = orientation.lower()

                elif line.startswith('%%Title:'):
                    params['title'] = line.split(':', 1)[1].strip()

                elif line.startswith('%%Creator:'):
                    params['creator'] = line.split(':', 1)[1].strip()

                elif line.startswith('%%Pages:'):
                    try:
                        params['pages'] = int(line.split(':')[1].strip())
                    except:
                        pass

    except Exception as e:
        logging.error(f"Error parseando PostScript: {e}")

    return params


# Clase helper para tests
class MockConverter:
    """Mock del conversor para testing sin GhostScript"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        return True

    def postscript_to_pdf(self, ps_file: Path, pdf_file: Path, quality: str = 'printer') -> bool:
        """Crea un PDF vacío para testing"""
        with open(pdf_file, 'wb') as f:
            f.write(b'%PDF-1.4\nMock PDF\n%%EOF')
        return True

    def stdin_to_pdf(self, stdin_data: bytes, pdf_file: Path, quality: str = 'printer') -> bool:
        return self.postscript_to_pdf(Path('dummy.ps'), pdf_file)

    def extract_page_count(self, pdf_file: Path) -> int:
        return 1
