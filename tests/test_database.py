"""
Tests para la capa de base de datos
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database.database import Database
from server.database.models import PrintJob, Client, ServerStats


@pytest.fixture
def test_db():
    """Fixture que crea una BD en memoria para tests"""
    db = Database(db_url="sqlite:///:memory:")
    yield db
    # Cleanup se hace automáticamente al terminar el test


class TestDatabase:
    """Tests para la clase Database"""

    def test_database_initialization(self, test_db):
        """Test inicialización de la BD"""
        assert test_db is not None
        assert test_db.engine is not None

    def test_create_print_job(self, test_db):
        """Test creación de trabajo de impresión"""
        job_data = {
            'job_id': 'TEST-001',
            'client_id': 'CLIENT-001',
            'user_name': 'test_user',
            'document_name': 'test.pdf',
            'file_format': 'pdf',
            'file_path': '/tmp/test.pdf',
            'page_count': 5,
            'status': 'pending'
        }

        job = test_db.create_print_job(job_data)

        assert job is not None
        assert job.job_id == 'TEST-001'
        assert job.user_name == 'test_user'
        assert job.page_count == 5

    def test_get_print_job(self, test_db):
        """Test recuperación de trabajo"""
        # Crear trabajo
        job_data = {
            'job_id': 'TEST-002',
            'client_id': 'CLIENT-001',
            'user_name': 'user2',
            'document_name': 'doc.pdf',
            'file_format': 'pdf',
            'file_path': '/tmp/doc.pdf',
            'status': 'pending'
        }
        test_db.create_print_job(job_data)

        # Recuperar
        job = test_db.get_print_job('TEST-002')

        assert job is not None
        assert job.job_id == 'TEST-002'
        assert job.user_name == 'user2'

    def test_update_print_job(self, test_db):
        """Test actualización de trabajo"""
        # Crear trabajo
        job_data = {
            'job_id': 'TEST-003',
            'client_id': 'CLIENT-001',
            'user_name': 'user3',
            'document_name': 'update.pdf',
            'file_format': 'pdf',
            'file_path': '/tmp/update.pdf',
            'status': 'pending'
        }
        test_db.create_print_job(job_data)

        # Actualizar
        test_db.update_print_job('TEST-003', {'status': 'completed'})

        # Verificar
        job = test_db.get_print_job('TEST-003')
        assert job.status == 'completed'

    def test_get_pending_jobs(self, test_db):
        """Test obtención de trabajos pendientes"""
        # Crear varios trabajos
        for i in range(5):
            job_data = {
                'job_id': f'TEST-{i+10}',
                'client_id': 'CLIENT-001',
                'user_name': f'user{i}',
                'document_name': f'doc{i}.pdf',
                'file_format': 'pdf',
                'file_path': f'/tmp/doc{i}.pdf',
                'status': 'pending',
                'priority': i + 1  # Diferentes prioridades
            }
            test_db.create_print_job(job_data)

        # Obtener pendientes
        pending = test_db.get_pending_jobs()

        assert len(pending) == 5
        # Verificar orden por prioridad
        assert pending[0].priority == 1
        assert pending[-1].priority == 5

    def test_create_client(self, test_db):
        """Test creación de cliente"""
        client = test_db.create_or_update_client(
            client_id='CLIENT-TEST',
            ip_address='192.168.1.100',
            hostname='test-pc'
        )

        assert client is not None
        assert client.client_id == 'CLIENT-TEST'
        assert client.ip_address == '192.168.1.100'

    def test_update_client(self, test_db):
        """Test actualización de cliente existente"""
        # Crear
        test_db.create_or_update_client(
            client_id='CLIENT-UPDATE',
            ip_address='192.168.1.100'
        )

        # Actualizar
        client = test_db.create_or_update_client(
            client_id='CLIENT-UPDATE',
            ip_address='192.168.1.200',
            hostname='updated-pc'
        )

        assert client.ip_address == '192.168.1.200'
        assert client.hostname == 'updated-pc'

    def test_get_summary(self, test_db):
        """Test resumen del sistema"""
        # Crear algunos trabajos
        for i in range(3):
            test_db.create_print_job({
                'job_id': f'SUM-{i}',
                'client_id': 'CLIENT-001',
                'user_name': 'user',
                'document_name': f'doc{i}.pdf',
                'file_format': 'pdf',
                'file_path': f'/tmp/doc{i}.pdf',
                'status': 'pending' if i < 2 else 'completed',
                'page_count': 10
            })

        # Obtener resumen
        summary = test_db.get_summary()

        assert summary['total_jobs'] == 3
        assert summary['pending_jobs'] == 2
        assert summary['completed_jobs'] == 1
        assert summary['total_pages'] == 30

    def test_count_jobs_by_status(self, test_db):
        """Test conteo de trabajos por estado"""
        # Crear trabajos
        statuses = ['pending', 'pending', 'completed', 'failed']
        for i, status in enumerate(statuses):
            test_db.create_print_job({
                'job_id': f'COUNT-{i}',
                'client_id': 'CLIENT-001',
                'user_name': 'user',
                'document_name': f'doc{i}.pdf',
                'file_format': 'pdf',
                'file_path': f'/tmp/doc{i}.pdf',
                'status': status
            })

        # Contar
        assert test_db.count_jobs_by_status('pending') == 2
        assert test_db.count_jobs_by_status('completed') == 1
        assert test_db.count_jobs_by_status('failed') == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
