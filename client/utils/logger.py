"""
Sistema de logging para el cliente
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:
    """Configurador de logging para el cliente"""

    def __init__(
        self,
        name: str = "printer_connect_client",
        log_file: Optional[Path] = None,
        log_level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
    ):
        """
        Inicializa el logger

        Args:
            name: Nombre del logger
            log_file: Ruta al archivo de log
            log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Tamaño máximo del archivo de log antes de rotar
            backup_count: Número de archivos de backup a mantener
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Evitar duplicación de handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Formato del log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Handler para archivo (si se especifica)
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Retorna el logger configurado"""
        return self.logger


def setup_logger(
    log_file: Optional[Path] = None,
    log_level: str = "INFO"
) -> logging.Logger:
    """
    Función helper para configurar rápidamente el logger

    Args:
        log_file: Ruta al archivo de log
        log_level: Nivel de logging

    Returns:
        Logger configurado
    """
    logger_instance = Logger(
        log_file=log_file,
        log_level=log_level
    )
    return logger_instance.get_logger()
