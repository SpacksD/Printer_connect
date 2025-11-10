"""
Gestor de configuración del servidor
"""

import configparser
from pathlib import Path
from typing import Optional, Any


class ConfigManager:
    """Gestiona la configuración del servidor"""

    DEFAULT_CONFIG = {
        'Server': {
            'host': '0.0.0.0',
            'port': '9100',
            'max_connections': '50',
            'enable_rest_api': 'false',
            'api_port': '8080',
        },
        'Security': {
            'enable_ssl': 'false',
            'ssl_cert_file': '',
            'ssl_key_file': '',
            'require_authentication': 'false',
            'jwt_secret_key': 'CHANGE_THIS_SECRET_KEY_IN_PRODUCTION',
            'jwt_expiration_minutes': '1440',
        },
        'Database': {
            'db_type': 'sqlite',
            'sqlite_file': './data/database.db',
        },
        'Printer': {
            'printer_name': '',
            'temp_folder': './temp',
            'archive_folder': './archive',
            'archive_retention_days': '30',
            'queue_check_interval': '2',
            'max_print_retries': '3',
        },
        'Logging': {
            'log_level': 'INFO',
            'log_file': './logs/server.log',
            'log_rotation_size': '50',
            'log_retention_count': '10',
        },
        'Monitoring': {
            'enable_prometheus': 'false',
            'prometheus_port': '9090',
        }
    }

    def __init__(self, config_file: Path):
        """
        Inicializa el gestor de configuración

        Args:
            config_file: Ruta al archivo de configuración
        """
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()

        # Crear archivo de configuración si no existe
        if not self.config_file.exists():
            self._create_default_config()
        else:
            self.load()

    def _create_default_config(self):
        """Crea un archivo de configuración con valores por defecto"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        for section, options in self.DEFAULT_CONFIG.items():
            self.config[section] = options

        self.save()

    def load(self):
        """Carga la configuración desde el archivo"""
        self.config.read(self.config_file, encoding='utf-8')

    def save(self):
        """Guarda la configuración al archivo"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def get(self, section: str, option: str, fallback: Optional[Any] = None) -> str:
        """
        Obtiene un valor de configuración

        Args:
            section: Sección de configuración
            option: Opción dentro de la sección
            fallback: Valor por defecto si no existe

        Returns:
            Valor de configuración
        """
        try:
            return self.config.get(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, option: str, fallback: int = 0) -> int:
        """Obtiene un valor entero de configuración"""
        try:
            return self.config.getint(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, option: str, fallback: bool = False) -> bool:
        """Obtiene un valor booleano de configuración"""
        try:
            return self.config.getboolean(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section: str, option: str, value: Any):
        """
        Establece un valor de configuración

        Args:
            section: Sección de configuración
            option: Opción dentro de la sección
            value: Valor a establecer
        """
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, option, str(value))

    def get_server_address(self) -> tuple[str, int]:
        """Retorna la dirección del servidor como tupla (host, port)"""
        host = self.get('Server', 'host', '0.0.0.0')
        port = self.get_int('Server', 'port', 9100)
        return (host, port)
