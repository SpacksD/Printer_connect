"""
Tests para los modelos de datos
"""

import pytest
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.data_models import (
    PrintMargins,
    PrintParameters,
    PrintJobMetadata,
    PageSize,
    Orientation
)


class TestPrintMargins:
    """Tests para PrintMargins"""

    def test_default_margins(self):
        """Test valores por defecto"""
        margins = PrintMargins()
        assert margins.top == 10.0
        assert margins.bottom == 10.0
        assert margins.left == 10.0
        assert margins.right == 10.0

    def test_custom_margins(self):
        """Test valores personalizados"""
        margins = PrintMargins(top=15, bottom=20, left=25, right=30)
        assert margins.top == 15
        assert margins.bottom == 20
        assert margins.left == 25
        assert margins.right == 30

    def test_to_dict(self):
        """Test conversión a diccionario"""
        margins = PrintMargins(top=5, bottom=10, left=15, right=20)
        d = margins.to_dict()

        assert d['top'] == 5
        assert d['bottom'] == 10
        assert d['left'] == 15
        assert d['right'] == 20

    def test_from_dict(self):
        """Test creación desde diccionario"""
        d = {'top': 5, 'bottom': 10, 'left': 15, 'right': 20}
        margins = PrintMargins.from_dict(d)

        assert margins.top == 5
        assert margins.bottom == 10
        assert margins.left == 15
        assert margins.right == 20


class TestPrintParameters:
    """Tests para PrintParameters"""

    def test_default_parameters(self):
        """Test valores por defecto"""
        params = PrintParameters()
        assert params.page_size == PageSize.A4
        assert params.orientation == Orientation.PORTRAIT
        assert params.copies == 1
        assert params.color is True
        assert params.duplex is False
        assert params.quality == 'normal'

    def test_custom_parameters(self):
        """Test valores personalizados"""
        params = PrintParameters(
            page_size=PageSize.LETTER,
            orientation=Orientation.LANDSCAPE,
            copies=2,
            color=False,
            duplex=True,
            quality='high'
        )

        assert params.page_size == PageSize.LETTER
        assert params.orientation == Orientation.LANDSCAPE
        assert params.copies == 2
        assert params.color is False
        assert params.duplex is True
        assert params.quality == 'high'

    def test_to_dict(self):
        """Test conversión a diccionario"""
        params = PrintParameters(
            page_size=PageSize.A4,
            orientation=Orientation.PORTRAIT
        )
        d = params.to_dict()

        assert d['page_size'] == 'A4'
        assert d['orientation'] == 'portrait'
        assert 'margins' in d
        assert 'copies' in d

    def test_from_dict(self):
        """Test creación desde diccionario"""
        d = {
            'page_size': 'LETTER',
            'orientation': 'landscape',
            'copies': 3,
            'color': False,
            'duplex': True,
            'quality': 'high',
            'margins': {'top': 5, 'bottom': 5, 'left': 5, 'right': 5}
        }
        params = PrintParameters.from_dict(d)

        assert params.page_size == PageSize.LETTER
        assert params.orientation == Orientation.LANDSCAPE
        assert params.copies == 3
        assert params.color is False
        assert params.duplex is True
        assert params.quality == 'high'


class TestPrintJobMetadata:
    """Tests para PrintJobMetadata"""

    def test_metadata_creation(self):
        """Test creación de metadata"""
        metadata = PrintJobMetadata(
            document_name='test.pdf',
            page_count=5,
            application='Test App',
            file_size_bytes=1024
        )

        assert metadata.document_name == 'test.pdf'
        assert metadata.page_count == 5
        assert metadata.application == 'Test App'
        assert metadata.file_size_bytes == 1024

    def test_to_dict(self):
        """Test conversión a diccionario"""
        metadata = PrintJobMetadata(
            document_name='doc.pdf',
            page_count=10
        )
        d = metadata.to_dict()

        assert d['document_name'] == 'doc.pdf'
        assert d['page_count'] == 10

    def test_from_dict(self):
        """Test creación desde diccionario"""
        d = {
            'document_name': 'report.pdf',
            'page_count': 20,
            'application': 'Word',
            'file_size_bytes': 2048
        }
        metadata = PrintJobMetadata.from_dict(d)

        assert metadata.document_name == 'report.pdf'
        assert metadata.page_count == 20
        assert metadata.application == 'Word'
        assert metadata.file_size_bytes == 2048


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
