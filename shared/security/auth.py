"""
Sistema de autenticación JWT para Printer_connect
Gestiona tokens, autenticación y autorización
"""

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class AuthenticationError(Exception):
    """Error de autenticación"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token expirado"""
    pass


class TokenInvalidError(AuthenticationError):
    """Token inválido"""
    pass


class AuthenticationManager:
    """
    Gestor de autenticación con JWT
    Genera y valida tokens de autenticación
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiration_hours: int = 24,
        algorithm: str = 'HS256',
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el gestor de autenticación

        Args:
            secret_key: Clave secreta para firmar tokens (se genera si es None)
            token_expiration_hours: Horas de validez del token
            algorithm: Algoritmo de firma (HS256, RS256, etc.)
            logger: Logger para mensajes
        """
        if not JWT_AVAILABLE:
            raise ImportError(
                "PyJWT no está instalado. "
                "Instala: pip install pyjwt"
            )

        self.logger = logger or logging.getLogger(__name__)
        self.algorithm = algorithm
        self.token_expiration_hours = token_expiration_hours

        # Generar o usar clave secreta
        if secret_key is None:
            self.secret_key = secrets.token_urlsafe(32)
            self.logger.warning(
                "No se proporcionó secret_key, se generó una aleatoria. "
                "Los tokens no serán válidos después de reiniciar el servidor."
            )
        else:
            self.secret_key = secret_key

        self.logger.info(
            f"AuthenticationManager inicializado (algorithm={algorithm}, "
            f"expiration={token_expiration_hours}h)"
        )

    def generate_token(
        self,
        client_id: str,
        username: Optional[str] = None,
        roles: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera un token JWT para un cliente

        Args:
            client_id: ID único del cliente
            username: Nombre de usuario (opcional)
            roles: Lista de roles (opcional)
            extra_claims: Claims adicionales

        Returns:
            Token JWT como string
        """
        now = datetime.utcnow()
        expiration = now + timedelta(hours=self.token_expiration_hours)

        # Claims básicos
        payload = {
            'client_id': client_id,
            'iat': now,  # Issued at
            'exp': expiration,  # Expiration
            'jti': secrets.token_urlsafe(16),  # JWT ID único
        }

        # Claims opcionales
        if username:
            payload['username'] = username
        if roles:
            payload['roles'] = roles
        if extra_claims:
            payload.update(extra_claims)

        # Generar token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        self.logger.info(
            f"Token generado para client_id='{client_id}', "
            f"expira en {self.token_expiration_hours}h"
        )

        return token

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Valida un token JWT y retorna sus claims

        Args:
            token: Token a validar

        Returns:
            Dictionary con los claims del token

        Raises:
            TokenExpiredError: Si el token expiró
            TokenInvalidError: Si el token es inválido
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            self.logger.debug(f"Token válido para client_id='{payload.get('client_id')}'")
            return payload

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expirado")
            raise TokenExpiredError("El token ha expirado")

        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Token inválido: {e}")
            raise TokenInvalidError(f"Token inválido: {e}")

    def refresh_token(self, old_token: str) -> str:
        """
        Renueva un token existente

        Args:
            old_token: Token antiguo a renovar

        Returns:
            Nuevo token JWT

        Raises:
            TokenInvalidError: Si el token es inválido
        """
        # Validar token antiguo
        payload = self.validate_token(old_token)

        # Generar nuevo token con los mismos claims
        return self.generate_token(
            client_id=payload['client_id'],
            username=payload.get('username'),
            roles=payload.get('roles'),
            extra_claims={
                k: v for k, v in payload.items()
                if k not in ['client_id', 'username', 'roles', 'iat', 'exp', 'jti']
            }
        )

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """
        Hash de contraseña con salt

        Args:
            password: Contraseña a hashear
            salt: Salt (se genera si es None)

        Returns:
            Tupla (hash_hex, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(32)

        # Usar PBKDF2 con SHA-256
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # 100k iteraciones
        )

        return hash_bytes.hex(), salt

    @staticmethod
    def verify_password(password: str, hash_hex: str, salt: bytes) -> bool:
        """
        Verifica una contraseña contra su hash

        Args:
            password: Contraseña a verificar
            hash_hex: Hash almacenado (hex)
            salt: Salt usado

        Returns:
            True si la contraseña es correcta
        """
        computed_hash, _ = AuthenticationManager.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, hash_hex)


class TokenValidator:
    """
    Validador de tokens más simple para uso en servidor
    """

    def __init__(
        self,
        auth_manager: AuthenticationManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el validador

        Args:
            auth_manager: Gestor de autenticación
            logger: Logger para mensajes
        """
        self.auth_manager = auth_manager
        self.logger = logger or logging.getLogger(__name__)

        # Cache de tokens validados (evita validar el mismo token múltiples veces)
        self._token_cache: Dict[str, Dict[str, Any]] = {}

    def validate(self, token: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Valida un token

        Args:
            token: Token a validar
            use_cache: Usar cache de validación

        Returns:
            Dictionary con claims del token

        Raises:
            AuthenticationError: Si el token no es válido
        """
        # Verificar cache
        if use_cache and token in self._token_cache:
            cached = self._token_cache[token]

            # Verificar que no haya expirado
            if datetime.utcnow().timestamp() < cached['exp']:
                return cached

            # Token en cache expiró, eliminar
            del self._token_cache[token]

        # Validar token
        try:
            payload = self.auth_manager.validate_token(token)

            # Guardar en cache
            if use_cache:
                self._token_cache[token] = payload

            return payload

        except AuthenticationError:
            raise

    def clear_cache(self):
        """Limpia el cache de tokens"""
        self._token_cache.clear()
        self.logger.debug("Cache de tokens limpiado")

    def has_role(self, token: str, required_role: str) -> bool:
        """
        Verifica si un token tiene un rol específico

        Args:
            token: Token a verificar
            required_role: Rol requerido

        Returns:
            True si el token tiene el rol
        """
        try:
            payload = self.validate(token)
            roles = payload.get('roles', [])
            return required_role in roles
        except AuthenticationError:
            return False

    def get_client_id(self, token: str) -> Optional[str]:
        """
        Obtiene el client_id de un token

        Args:
            token: Token

        Returns:
            Client ID o None si el token es inválido
        """
        try:
            payload = self.validate(token)
            return payload.get('client_id')
        except AuthenticationError:
            return None
