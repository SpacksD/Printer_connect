"""
Excepciones personalizadas para Printer_connect
"""


class PrinterConnectException(Exception):
    """Excepción base para todas las excepciones del sistema"""
    pass


class ConnectionError(PrinterConnectException):
    """Error de conexión con el servidor"""
    pass


class AuthenticationError(PrinterConnectException):
    """Error de autenticación"""
    pass


class InvalidParametersError(PrinterConnectException):
    """Parámetros de impresión inválidos"""
    pass


class PrinterNotFoundError(PrinterConnectException):
    """Impresora no encontrada"""
    pass


class PrintJobError(PrinterConnectException):
    """Error al procesar trabajo de impresión"""
    pass


class FileFormatError(PrinterConnectException):
    """Formato de archivo no soportado"""
    pass


class FileSizeError(PrinterConnectException):
    """Archivo excede el tamaño máximo permitido"""
    pass


class QueueFullError(PrinterConnectException):
    """Cola de impresión llena"""
    pass


class ServerError(PrinterConnectException):
    """Error interno del servidor"""
    pass


class DatabaseError(PrinterConnectException):
    """Error de base de datos"""
    pass


class ConfigurationError(PrinterConnectException):
    """Error de configuración"""
    pass
