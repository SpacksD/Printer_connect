"""
Tests para la API REST (Fase 5)
"""

import sys
from pathlib import Path
import pytest

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi.testclient import TestClient
    from server.api.main import app
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI no está instalado")
class TestAPI:
    """Tests para la API REST"""

    @pytest.fixture
    def client(self):
        """Fixture para el cliente de testing"""
        return TestClient(app)

    def test_health_check(self, client):
        """Test del endpoint de health check"""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_login_invalid_credentials(self, client):
        """Test de login con credenciales inválidas"""
        response = client.post("/api/auth/login", json={
            "username": "invalid_user",
            "password": "invalid_password"
        })
        assert response.status_code == 401

    def test_unauthorized_access(self, client):
        """Test de acceso sin autenticación"""
        response = client.get("/api/users")
        assert response.status_code == 403  # No credentials provided

    def test_invalid_token(self, client):
        """Test con token inválido"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI no está instalado")
class TestAPIIntegration:
    """Tests de integración de la API"""

    @pytest.fixture
    def client(self):
        """Fixture para el cliente de testing"""
        return TestClient(app)

    @pytest.fixture
    def auth_token(self, client):
        """Fixture para obtener token de autenticación"""
        # Nota: Este test requiere que exista un usuario admin
        # En un entorno de testing, deberías crear un usuario de prueba
        return None  # Placeholder

    def test_full_user_workflow(self, client, auth_token):
        """Test del flujo completo de gestión de usuarios"""
        if not auth_token:
            pytest.skip("Requiere usuario admin configurado")

        headers = {"Authorization": f"Bearer {auth_token}"}

        # Crear usuario
        response = client.post("/api/users", headers=headers, json={
            "username": "test_user",
            "password": "test_password",
            "email": "test@example.com",
            "role": "user"
        })
        assert response.status_code == 201

        user_data = response.json()
        user_id = user_data["id"]

        # Listar usuarios
        response = client.get("/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert any(u["id"] == user_id for u in users)

        # Actualizar usuario
        response = client.put(f"/api/users/{user_id}", headers=headers, json={
            "full_name": "Test User Full Name"
        })
        assert response.status_code == 200

        # Eliminar usuario
        response = client.delete(f"/api/users/{user_id}", headers=headers)
        assert response.status_code == 204


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
