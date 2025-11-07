"""
Constantes compartidas entre cliente y servidor
"""

# Versión del protocolo
PROTOCOL_VERSION = "1.0"

# Puerto por defecto
DEFAULT_PORT = 9100  # Puerto estándar de impresoras

# Tamaños de buffer
BUFFER_SIZE = 8192
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Tipos de mensaje
MESSAGE_TYPE_PRINT_JOB = "print_job"
MESSAGE_TYPE_STATUS_REQUEST = "status_request"
MESSAGE_TYPE_RESPONSE = "response"
MESSAGE_TYPE_AUTH = "authentication"
MESSAGE_TYPE_HEARTBEAT = "heartbeat"

# Estados de trabajo de impresión
STATUS_PENDING = "pending"
STATUS_PRINTING = "printing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

# Formatos de archivo soportados
SUPPORTED_FORMATS = ["pdf", "postscript", "xps"]

# Tamaños de página estándar (en mm)
PAGE_SIZES = {
    "A4": (210, 297),
    "A3": (297, 420),
    "A5": (148, 210),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}

# Orientaciones
ORIENTATION_PORTRAIT = "portrait"
ORIENTATION_LANDSCAPE = "landscape"

# Calidad de impresión
QUALITY_DRAFT = "draft"
QUALITY_NORMAL = "normal"
QUALITY_HIGH = "high"

# Timeouts (en segundos)
CONNECTION_TIMEOUT = 30
RESPONSE_TIMEOUT = 60
HEARTBEAT_INTERVAL = 300  # 5 minutos

# Reintentos
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
