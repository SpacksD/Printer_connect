"""
Tests para el módulo de seguridad (Fase 4)
"""

import sys
import secrets
from pathlib import Path

import pytest

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.security.validation import InputValidator, ValidationError
from shared.security.rate_limiter import RateLimiter, RateLimitExceeded

# Tests de JWT requieren pyjwt
try:
    from shared.security.auth import AuthenticationManager, TokenValidator, TokenExpiredError, TokenInvalidError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class TestInputValidator:
    """Tests para InputValidator"""

    def test_validate_client_id_valid(self):
        """Test validación de client_id válido"""
        validator = InputValidator()

        valid_ids = [
            'client_123',
            'test-client',
            'ABC_123',
            'user1'
        ]

        for client_id in valid_ids:
            result = validator.validate_client_id(client_id)
            assert result == client_id

    def test_validate_client_id_invalid(self):
        """Test validación de client_id inválido"""
        validator = InputValidator()

        invalid_ids = [
            '',  # Vacío
            'client@123',  # Caracteres especiales
            'a' * 101,  # Muy largo
            'client 123',  # Espacios
            'client/123',  # Slash
        ]

        for client_id in invalid_ids:
            with pytest.raises(ValidationError):
                validator.validate_client_id(client_id)

    def test_validate_username_valid(self):
        """Test validación de username válido"""
        validator = InputValidator()

        valid_usernames = [
            'john_doe',
            'user.123',
            'test-user',
            'abc'
        ]

        for username in valid_usernames:
            result = validator.validate_username(username)
            assert result == username

    def test_validate_username_invalid(self):
        """Test validación de username inválido"""
        validator = InputValidator()

        invalid_usernames = [
            '',  # Vacío
            'ab',  # Muy corto
            'user@name',  # Caracteres especiales
            'a' * 51,  # Muy largo
        ]

        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                validator.validate_username(username)

    def test_validate_string(self):
        """Test validación de string genérico"""
        validator = InputValidator()

        # Válido
        result = validator.validate_string(
            "test string",
            field_name="test",
            min_length=5,
            max_length=20
        )
        assert result == "test string"

        # Muy corto
        with pytest.raises(ValidationError):
            validator.validate_string(
                "ab",
                field_name="test",
                min_length=5
            )

        # Muy largo
        with pytest.raises(ValidationError):
            validator.validate_string(
                "a" * 100,
                field_name="test",
                max_length=50
            )

    def test_validate_integer(self):
        """Test validación de enteros"""
        validator = InputValidator()

        # Válido
        assert validator.validate_integer(10, min_value=0, max_value=100) == 10

        # Muy pequeño
        with pytest.raises(ValidationError):
            validator.validate_integer(-5, min_value=0)

        # Muy grande
        with pytest.raises(ValidationError):
            validator.validate_integer(200, max_value=100)

        # No es entero
        with pytest.raises(ValidationError):
            validator.validate_integer("not_an_int")

    def test_validate_enum(self):
        """Test validación de enum"""
        validator = InputValidator()

        allowed_values = ['option1', 'option2', 'option3']

        # Válido
        assert validator.validate_enum('option1', allowed_values) == 'option1'

        # Inválido
        with pytest.raises(ValidationError):
            validator.validate_enum('option4', allowed_values)

    def test_sanitize_path(self):
        """Test sanitización de rutas"""
        validator = InputValidator()

        # Detectar path traversal
        with pytest.raises(ValidationError):
            validator.sanitize_path(Path('../../../etc/passwd'))


class TestRateLimiter:
    """Tests para RateLimiter"""

    def test_rate_limiter_basic(self):
        """Test básico de rate limiting"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)

        # Debería permitir hasta burst_size requests inmediatas
        for i in range(10):
            assert limiter.check_rate_limit('client1', raise_on_limit=False)

        # La siguiente debería fallar (burst agotado)
        assert not limiter.check_rate_limit('client1', raise_on_limit=False)

    def test_rate_limiter_per_client(self):
        """Test que el rate limiting es por cliente"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)

        # Cliente 1 agota su burst
        for i in range(5):
            limiter.check_rate_limit('client1', raise_on_limit=False)

        # Cliente 1 no puede hacer más requests
        assert not limiter.check_rate_limit('client1', raise_on_limit=False)

        # Cliente 2 puede hacer requests (tiene su propio bucket)
        assert limiter.check_rate_limit('client2', raise_on_limit=False)

    def test_rate_limiter_exception(self):
        """Test que se lanza excepción cuando se excede el límite"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=3)

        # Agotar burst
        for i in range(3):
            limiter.check_rate_limit('client1')

        # Debería lanzar excepción
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit('client1', raise_on_limit=True)

    def test_rate_limiter_reset(self):
        """Test reset de rate limit"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)

        # Agotar burst
        for i in range(5):
            limiter.check_rate_limit('client1')

        # Resetear
        limiter.reset_client('client1')

        # Debería poder hacer requests de nuevo
        assert limiter.check_rate_limit('client1', raise_on_limit=False)

    def test_get_remaining_requests(self):
        """Test obtención de requests restantes"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)

        # Al inicio debería tener burst_size tokens
        assert limiter.get_remaining_requests('client1') == 10

        # Después de consumir algunos
        limiter.check_rate_limit('client1')
        limiter.check_rate_limit('client1')

        assert limiter.get_remaining_requests('client1') == 8


@pytest.mark.skipif(not JWT_AVAILABLE, reason="PyJWT no está instalado")
class TestAuthenticationManager:
    """Tests para AuthenticationManager"""

    def test_generate_token(self):
        """Test generación de token"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user',
            roles=['user']
        )

        assert token
        assert isinstance(token, str)

    def test_validate_token(self):
        """Test validación de token"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        # Generar token
        token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user',
            roles=['user', 'admin']
        )

        # Validar token
        payload = auth_manager.validate_token(token)

        assert payload['client_id'] == 'test_client'
        assert payload['username'] == 'test_user'
        assert payload['roles'] == ['user', 'admin']

    def test_invalid_token(self):
        """Test token inválido"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        # Token inválido
        with pytest.raises(TokenInvalidError):
            auth_manager.validate_token('invalid_token_here')

    def test_refresh_token(self):
        """Test renovación de token"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        # Generar token original
        old_token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user'
        )

        # Renovar token
        new_token = auth_manager.refresh_token(old_token)

        assert new_token
        assert new_token != old_token

        # Validar nuevo token
        payload = auth_manager.validate_token(new_token)
        assert payload['client_id'] == 'test_client'

    def test_hash_password(self):
        """Test hash de contraseña"""
        password = 'my_secure_password'

        hash_hex, salt = AuthenticationManager.hash_password(password)

        assert hash_hex
        assert salt
        assert len(hash_hex) == 64  # SHA-256 hex = 64 caracteres

    def test_verify_password(self):
        """Test verificación de contraseña"""
        password = 'my_secure_password'

        # Hash password
        hash_hex, salt = AuthenticationManager.hash_password(password)

        # Verificar correcta
        assert AuthenticationManager.verify_password(password, hash_hex, salt)

        # Verificar incorrecta
        assert not AuthenticationManager.verify_password('wrong_password', hash_hex, salt)


@pytest.mark.skipif(not JWT_AVAILABLE, reason="PyJWT no está instalado")
class TestTokenValidator:
    """Tests para TokenValidator"""

    def test_token_validator_basic(self):
        """Test básico de TokenValidator"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        validator = TokenValidator(auth_manager)

        # Generar token
        token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user',
            roles=['user']
        )

        # Validar
        payload = validator.validate(token)

        assert payload['client_id'] == 'test_client'

    def test_token_validator_cache(self):
        """Test cache de tokens"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        validator = TokenValidator(auth_manager)

        # Generar token
        token = auth_manager.generate_token(client_id='test_client')

        # Primera validación (sin cache)
        payload1 = validator.validate(token, use_cache=True)

        # Segunda validación (desde cache)
        payload2 = validator.validate(token, use_cache=True)

        assert payload1 == payload2

        # Limpiar cache
        validator.clear_cache()

    def test_has_role(self):
        """Test verificación de roles"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        validator = TokenValidator(auth_manager)

        # Token con rol 'admin'
        token = auth_manager.generate_token(
            client_id='test_client',
            roles=['user', 'admin']
        )

        assert validator.has_role(token, 'admin')
        assert validator.has_role(token, 'user')
        assert not validator.has_role(token, 'superadmin')

    def test_get_client_id(self):
        """Test obtención de client_id"""
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key',
            token_expiration_hours=1
        )

        validator = TokenValidator(auth_manager)

        # Token válido
        token = auth_manager.generate_token(client_id='test_client_123')

        client_id = validator.get_client_id(token)
        assert client_id == 'test_client_123'

        # Token inválido
        client_id = validator.get_client_id('invalid_token')
        assert client_id is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
