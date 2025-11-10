"""
Tests para el conversor de formatos
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from client.printer_driver.converter import (
    FormatConverter,
    MockConverter,
    parse_postscript_params
)


class TestFormatConverter:
    """Tests para FormatConverter"""

    def test_converter_initialization(self):
        """Test inicialización del conversor"""
        converter = FormatConverter()
        assert converter is not None

    def test_is_available(self):
        """Test verificación de disponibilidad"""
        converter = FormatConverter()
        # El resultado depende de si GhostScript está instalado
        result = converter.is_available()
        assert isinstance(result, bool)

    def test_find_ghostscript(self):
        """Test búsqueda de GhostScript"""
        converter = FormatConverter()
        # gs_path puede ser None si no está instalado
        assert converter.gs_path is None or isinstance(converter.gs_path, Path)


class TestMockConverter:
    """Tests para MockConverter"""

    def test_mock_is_available(self):
        """Test que el mock siempre está disponible"""
        converter = MockConverter()
        assert converter.is_available() is True

    def test_mock_conversion(self, tmp_path):
        """Test conversión con mock"""
        converter = MockConverter()

        ps_file = tmp_path / "test.ps"
        pdf_file = tmp_path / "test.pdf"

        # Crear archivo PS dummy
        with open(ps_file, 'w') as f:
            f.write("%!PS-Adobe-3.0\n%%EOF")

        # Convertir
        result = converter.postscript_to_pdf(ps_file, pdf_file)

        assert result is True
        assert pdf_file.exists()

        # Verificar que el PDF fue creado
        with open(pdf_file, 'rb') as f:
            content = f.read()
            assert b'%PDF' in content

    def test_mock_extract_page_count(self, tmp_path):
        """Test extracción de número de páginas con mock"""
        converter = MockConverter()

        pdf_file = tmp_path / "test.pdf"
        with open(pdf_file, 'wb') as f:
            f.write(b'%PDF-1.4\nMock\n%%EOF')

        page_count = converter.extract_page_count(pdf_file)
        assert page_count == 1


class TestPostScriptParser:
    """Tests para el parser de PostScript"""

    def test_parse_empty_file(self, tmp_path):
        """Test parsear archivo vacío"""
        ps_file = tmp_path / "empty.ps"
        ps_file.write_text("")

        params = parse_postscript_params(ps_file)

        assert isinstance(params, dict)
        assert 'page_size' in params
        assert 'orientation' in params

    def test_parse_with_dsc_comments(self, tmp_path):
        """Test parsear PostScript con comentarios DSC"""
        ps_file = tmp_path / "test.ps"

        content = """
%!PS-Adobe-3.0
%%Title: Test Document
%%Creator: Test Application
%%Pages: 5
%%BoundingBox: 0 0 612 792
%%Orientation: Portrait
%%EndComments
"""
        ps_file.write_text(content)

        params = parse_postscript_params(ps_file)

        assert params['title'] == 'Test Document'
        assert params['creator'] == 'Test Application'
        assert params['pages'] == 5
        assert params['page_size'] == 'Letter'  # 612x792 es Letter
        assert params['orientation'] == 'portrait'

    def test_parse_a4_size(self, tmp_path):
        """Test reconocimiento de tamaño A4"""
        ps_file = tmp_path / "a4.ps"

        content = """
%!PS-Adobe-3.0
%%BoundingBox: 0 0 595 842
%%EndComments
"""
        ps_file.write_text(content)

        params = parse_postscript_params(ps_file)
        assert params['page_size'] == 'A4'  # 595x842 es A4

    def test_parse_landscape(self, tmp_path):
        """Test reconocimiento de orientación landscape"""
        ps_file = tmp_path / "landscape.ps"

        content = """
%!PS-Adobe-3.0
%%Orientation: Landscape
%%EndComments
"""
        ps_file.write_text(content)

        params = parse_postscript_params(ps_file)
        assert params['orientation'] == 'landscape'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
