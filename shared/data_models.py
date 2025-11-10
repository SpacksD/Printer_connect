"""
Modelos de datos compartidos entre cliente y servidor
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class PrintJobStatus(Enum):
    """Estados posibles de un trabajo de impresión"""
    PENDING = "pending"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageSize(Enum):
    """Tamaños de página soportados"""
    A4 = "A4"
    A3 = "A3"
    A5 = "A5"
    LETTER = "Letter"
    LEGAL = "Legal"


class Orientation(Enum):
    """Orientaciones de página"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass
class PrintMargins:
    """Márgenes de impresión en milímetros"""
    top: float = 10.0
    bottom: float = 10.0
    left: float = 10.0
    right: float = 10.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'PrintMargins':
        return cls(
            top=data.get("top", 10.0),
            bottom=data.get("bottom", 10.0),
            left=data.get("left", 10.0),
            right=data.get("right", 10.0)
        )


@dataclass
class PrintParameters:
    """Parámetros de impresión"""
    page_size: PageSize = PageSize.A4
    orientation: Orientation = Orientation.PORTRAIT
    margins: PrintMargins = field(default_factory=PrintMargins)
    copies: int = 1
    color: bool = True
    duplex: bool = False
    quality: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_size": self.page_size.value,
            "orientation": self.orientation.value,
            "margins": self.margins.to_dict(),
            "copies": self.copies,
            "color": self.color,
            "duplex": self.duplex,
            "quality": self.quality
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrintParameters':
        return cls(
            page_size=PageSize(data.get("page_size", "A4")),
            orientation=Orientation(data.get("orientation", "portrait")),
            margins=PrintMargins.from_dict(data.get("margins", {})),
            copies=data.get("copies", 1),
            color=data.get("color", True),
            duplex=data.get("duplex", False),
            quality=data.get("quality", "normal")
        )


@dataclass
class PrintJobMetadata:
    """Metadatos del trabajo de impresión"""
    document_name: str
    page_count: int
    application: Optional[str] = None
    file_size_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "page_count": self.page_count,
            "application": self.application,
            "file_size_bytes": self.file_size_bytes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrintJobMetadata':
        return cls(
            document_name=data["document_name"],
            page_count=data["page_count"],
            application=data.get("application"),
            file_size_bytes=data.get("file_size_bytes")
        )


@dataclass
class PrintJob:
    """Trabajo de impresión completo"""
    job_id: str
    client_id: str
    user: str
    timestamp: datetime
    file_content: bytes
    file_format: str
    parameters: PrintParameters
    metadata: PrintJobMetadata
    status: PrintJobStatus = PrintJobStatus.PENDING
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario (sin incluir file_content por tamaño)"""
        return {
            "job_id": self.job_id,
            "client_id": self.client_id,
            "user": self.user,
            "timestamp": self.timestamp.isoformat(),
            "file_format": self.file_format,
            "parameters": self.parameters.to_dict(),
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "error_message": self.error_message
        }


@dataclass
class ServerResponse:
    """Respuesta del servidor"""
    status: str  # "success" o "error"
    message: str
    job_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    queue_position: Optional[int] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "queue_position": self.queue_position,
            "error_code": self.error_code
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerResponse':
        return cls(
            status=data["status"],
            message=data["message"],
            job_id=data.get("job_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            queue_position=data.get("queue_position"),
            error_code=data.get("error_code")
        )
