"""
Gestor de configuración del cliente
"""

import configparser
from pathlib import Path
from typing import Optional, Any
import uuid


class ConfigManager:
    """Gestiona la configuración del cliente"""

    DEFAULT_CONFIG = {
        'Server': {
            'host': '127.0.0.1',
            'port': '9100',
            'connection_timeout': '30',
        },
        'Authentication': {
            'username': '',
        },
        'Client': {
            'client_id': '',
            'printer_name': 'Printer_connect',
            'temp_folder': './temp',
            'queue_folder': './queue',
        },
        'Printing': {
            'default_page_size': 'A4',
            'default_orientation': 'portrait',
            'default_color': 'true',
            'default_duplex': 'false',
            'default_quality': 'normal',
            'enable_compression': 'true',
        },
        'Logging': {
            'log_level': 'INFO',
            'log_file': './logs/client.log',
            'log_rotation_size': '10',
            'log_retention_count': '5',
        },
        'UI': {
            'show_notifications': 'true',
            'minimize_to_tray': 'true',
            'start_with_windows': 'false',
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

        # Generar client_id si no existe
        if not self.get('Client', 'client_id'):
            self.set('Client', 'client_id', str(uuid.uuid4()))
            self.save()

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
        host = self.get('Server', 'host', '127.0.0.1')
        port = self.get_int('Server', 'port', 9100)
        return (host, port)
