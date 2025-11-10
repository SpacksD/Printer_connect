"""
Modelos de base de datos para Printer_connect
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, Float,
    create_engine, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Optional

Base = declarative_base()


class PrintJob(Base):
    """Modelo de trabajo de impresión"""
    __tablename__ = 'print_jobs'

    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    client_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(100), nullable=False, index=True)

    # Archivo
    document_name = Column(String(255), nullable=False)
    file_format = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer)
    file_path = Column(String(500))  # Ruta al archivo en el servidor

    # Parámetros de impresión
    page_size = Column(String(20))
    orientation = Column(String(20))
    copies = Column(Integer, default=1)
    color = Column(Boolean, default=True)
    duplex = Column(Boolean, default=False)
    quality = Column(String(20))

    # Márgenes
    margin_top = Column(Float)
    margin_bottom = Column(Float)
    margin_left = Column(Float)
    margin_right = Column(Float)

    # Metadatos
    page_count = Column(Integer)
    application = Column(String(100))

    # Estado
    status = Column(String(20), nullable=False, default='pending', index=True)
    # Estados: pending, printing, completed, failed, cancelled

    priority = Column(Integer, default=5, index=True)  # 1=alta, 10=baja
    queue_position = Column(Integer)

    # Resultados
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Tiempos de procesamiento
    processing_time_ms = Column(Integer)

    # Índices compuestos
    __table_args__ = (
        Index('idx_status_priority', 'status', 'priority'),
        Index('idx_user_created', 'user_name', 'created_at'),
    )

    def __repr__(self):
        return f"<PrintJob(job_id='{self.job_id}', status='{self.status}', user='{self.user_name}')>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'client_id': self.client_id,
            'user_name': self.user_name,
            'document_name': self.document_name,
            'file_format': self.file_format,
            'file_size_bytes': self.file_size_bytes,
            'page_size': self.page_size,
            'orientation': self.orientation,
            'copies': self.copies,
            'color': self.color,
            'duplex': self.duplex,
            'quality': self.quality,
            'page_count': self.page_count,
            'application': self.application,
            'status': self.status,
            'priority': self.priority,
            'queue_position': self.queue_position,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processing_time_ms': self.processing_time_ms
        }


class Client(Base):
    """Modelo de cliente conectado"""
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(100), unique=True, nullable=False, index=True)
    hostname = Column(String(100))
    ip_address = Column(String(50))

    # Estado
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)

    # Estadísticas
    total_jobs = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Client(client_id='{self.client_id}', ip='{self.ip_address}')>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'is_active': self.is_active,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'total_jobs': self.total_jobs,
            'total_pages': self.total_pages,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ServerStats(Base):
    """Modelo de estadísticas del servidor por día"""
    __tablename__ = 'server_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)

    # Estadísticas de trabajos
    total_jobs = Column(Integer, default=0)
    completed_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    cancelled_jobs = Column(Integer, default=0)

    # Estadísticas de páginas
    total_pages = Column(Integer, default=0)

    # Tiempos
    avg_processing_time_ms = Column(Integer)
    uptime_seconds = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ServerStats(date='{self.date.date()}', jobs={self.total_jobs})>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'cancelled_jobs': self.cancelled_jobs,
            'total_pages': self.total_pages,
            'avg_processing_time_ms': self.avg_processing_time_ms,
            'uptime_seconds': self.uptime_seconds
        }


class User(Base):
    """Modelo de usuario del sistema"""
    __tablename__ = 'users'

    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)

    # Autenticación
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)

    # Información
    full_name = Column(String(100))
    role = Column(String(20), default='user', index=True)  # admin, user, viewer

    # Estado
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    last_activity = Column(DateTime)

    # Configuración
    preferences = Column(Text)  # JSON con preferencias del usuario

    # Índices compuestos
    __table_args__ = (
        Index('idx_user_active_role', 'is_active', 'role'),
    )

    def to_dict(self, include_sensitive=False) -> dict:
        """Convierte el usuario a diccionario"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
        }

        if include_sensitive:
            data['password_hash'] = self.password_hash
            data['password_salt'] = self.password_salt

        return data
