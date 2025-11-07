"""
Validación de inputs y sanitización
Previene inyecciones y otros ataques
"""

import re
import logging
from pathlib import Path
from typing import Optional, Any, List


class ValidationError(Exception):
    """Error de validación"""
    pass


class InputValidator:
    """
    Validador de inputs para prevenir ataques
    """

    # Tamaños máximos por defecto
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_STRING_LENGTH = 1000
    MAX_CLIENT_ID_LENGTH = 100
    MAX_USERNAME_LENGTH = 50
    MAX_DOCUMENT_NAME_LENGTH = 255

    # Formatos permitidos por defecto
    ALLOWED_FILE_EXTENSIONS = {'.pdf', '.ps', '.postscript'}

    # Regex para validaciones
    REGEX_CLIENT_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
    REGEX_USERNAME = re.compile(r'^[a-zA-Z0-9_.-]{3,50}$')
    REGEX_JOB_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
    REGEX_SAFE_STRING = re.compile(r'^[a-zA-Z0-9\s_.-]{1,1000}$')

    def __init__(
        self,
        max_file_size: Optional[int] = None,
        allowed_extensions: Optional[set] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el validador

        Args:
            max_file_size: Tamaño máximo de archivo en bytes
            allowed_extensions: Extensiones de archivo permitidas
            logger: Logger para mensajes
        """
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.allowed_extensions = allowed_extensions or self.ALLOWED_FILE_EXTENSIONS
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info(
            f"InputValidator inicializado (max_size={self.max_file_size}, "
            f"extensions={self.allowed_extensions})"
        )

    def validate_client_id(self, client_id: str) -> str:
        """
        Valida un client_id

        Args:
            client_id: Client ID a validar

        Returns:
            Client ID sanitizado

        Raises:
            ValidationError: Si no es válido
        """
        if not client_id:
            raise ValidationError("client_id no puede estar vacío")

        if len(client_id) > self.MAX_CLIENT_ID_LENGTH:
            raise ValidationError(
                f"client_id demasiado largo (max {self.MAX_CLIENT_ID_LENGTH})"
            )

        if not self.REGEX_CLIENT_ID.match(client_id):
            raise ValidationError(
                "client_id contiene caracteres inválidos "
                "(solo: a-z, A-Z, 0-9, _, -)"
            )

        return client_id

    def validate_username(self, username: str) -> str:
        """
        Valida un nombre de usuario

        Args:
            username: Username a validar

        Returns:
            Username sanitizado

        Raises:
            ValidationError: Si no es válido
        """
        if not username:
            raise ValidationError("username no puede estar vacío")

        if len(username) > self.MAX_USERNAME_LENGTH:
            raise ValidationError(
                f"username demasiado largo (max {self.MAX_USERNAME_LENGTH})"
            )

        if not self.REGEX_USERNAME.match(username):
            raise ValidationError(
                "username contiene caracteres inválidos "
                "(solo: a-z, A-Z, 0-9, _, ., -, mínimo 3 caracteres)"
            )

        return username

    def validate_job_id(self, job_id: str) -> str:
        """
        Valida un job_id

        Args:
            job_id: Job ID a validar

        Returns:
            Job ID sanitizado

        Raises:
            ValidationError: Si no es válido
        """
        if not job_id:
            raise ValidationError("job_id no puede estar vacío")

        if not self.REGEX_JOB_ID.match(job_id):
            raise ValidationError(
                "job_id contiene caracteres inválidos "
                "(solo: a-z, A-Z, 0-9, _, -)"
            )

        return job_id

    def validate_file_path(self, file_path: Path) -> Path:
        """
        Valida una ruta de archivo

        Args:
            file_path: Ruta a validar

        Returns:
            Path validado

        Raises:
            ValidationError: Si no es válido
        """
        if not file_path:
            raise ValidationError("file_path no puede estar vacío")

        # Convertir a Path si es string
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Verificar que existe
        if not file_path.exists():
            raise ValidationError(f"Archivo no existe: {file_path}")

        # Verificar que es un archivo (no directorio)
        if not file_path.is_file():
            raise ValidationError(f"No es un archivo: {file_path}")

        # Verificar extensión
        if file_path.suffix.lower() not in self.allowed_extensions:
            raise ValidationError(
                f"Extensión no permitida: {file_path.suffix}. "
                f"Permitidas: {self.allowed_extensions}"
            )

        # Verificar tamaño
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValidationError(
                f"Archivo demasiado grande: {file_size} bytes "
                f"(max {self.max_file_size})"
            )

        # Verificar path traversal
        try:
            resolved = file_path.resolve()
            # Esto previene ataques de path traversal
        except Exception as e:
            raise ValidationError(f"Ruta inválida: {e}")

        return file_path

    def validate_document_name(self, document_name: str) -> str:
        """
        Valida un nombre de documento

        Args:
            document_name: Nombre a validar

        Returns:
            Nombre sanitizado

        Raises:
            ValidationError: Si no es válido
        """
        if not document_name:
            raise ValidationError("document_name no puede estar vacío")

        if len(document_name) > self.MAX_DOCUMENT_NAME_LENGTH:
            raise ValidationError(
                f"document_name demasiado largo (max {self.MAX_DOCUMENT_NAME_LENGTH})"
            )

        # Remover caracteres peligrosos
        # Permitir alfanuméricos, espacios, guiones, puntos y paréntesis
        sanitized = re.sub(r'[^a-zA-Z0-9\s_.()\-]', '', document_name)

        if not sanitized:
            raise ValidationError("document_name contiene solo caracteres inválidos")

        return sanitized

    def validate_string(
        self,
        value: str,
        field_name: str = "field",
        min_length: int = 0,
        max_length: Optional[int] = None,
        allow_empty: bool = False
    ) -> str:
        """
        Valida un string genérico

        Args:
            value: Valor a validar
            field_name: Nombre del campo (para mensajes de error)
            min_length: Longitud mínima
            max_length: Longitud máxima
            allow_empty: Permitir strings vacíos

        Returns:
            String validado

        Raises:
            ValidationError: Si no es válido
        """
        if value is None:
            if allow_empty:
                return ""
            raise ValidationError(f"{field_name} no puede ser None")

        if not isinstance(value, str):
            raise ValidationError(f"{field_name} debe ser string")

        if len(value) < min_length:
            raise ValidationError(
                f"{field_name} demasiado corto (min {min_length})"
            )

        if max_length and len(value) > max_length:
            raise ValidationError(
                f"{field_name} demasiado largo (max {max_length})"
            )

        return value

    def validate_integer(
        self,
        value: Any,
        field_name: str = "field",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """
        Valida un entero

        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_value: Valor mínimo
            max_value: Valor máximo

        Returns:
            Entero validado

        Raises:
            ValidationError: Si no es válido
        """
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValidationError(f"{field_name} debe ser un entero")

        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} demasiado pequeño (min {min_value})"
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} demasiado grande (max {max_value})"
            )

        return value

    def validate_enum(
        self,
        value: str,
        allowed_values: List[str],
        field_name: str = "field"
    ) -> str:
        """
        Valida que un valor esté en una lista permitida

        Args:
            value: Valor a validar
            allowed_values: Valores permitidos
            field_name: Nombre del campo

        Returns:
            Valor validado

        Raises:
            ValidationError: Si no es válido
        """
        if value not in allowed_values:
            raise ValidationError(
                f"{field_name} inválido. "
                f"Valores permitidos: {allowed_values}"
            )

        return value

    def sanitize_path(self, path: Path) -> Path:
        """
        Sanitiza una ruta de archivo para prevenir path traversal

        Args:
            path: Ruta a sanitizar

        Returns:
            Ruta sanitizada

        Raises:
            ValidationError: Si la ruta es peligrosa
        """
        # Convertir a Path
        if isinstance(path, str):
            path = Path(path)

        # Resolver path
        try:
            resolved = path.resolve()
        except Exception as e:
            raise ValidationError(f"Ruta inválida: {e}")

        # Verificar que no contiene ".."
        if '..' in path.parts:
            raise ValidationError("Ruta contiene '..' (path traversal)")

        return resolved
