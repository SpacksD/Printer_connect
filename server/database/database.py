"""
Capa de acceso a datos para Printer_connect
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from server.database.models import Base, PrintJob, Client, ServerStats, User


class Database:
    """Gestor de base de datos"""

    def __init__(
        self,
        db_url: str = "sqlite:///./data/printer_connect.db",
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa la conexión a la base de datos

        Args:
            db_url: URL de conexión (sqlite:// o postgresql://)
            logger: Logger para mensajes
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_url = db_url

        # Crear carpeta para SQLite si es necesario
        if db_url.startswith('sqlite:///'):
            db_path = Path(db_url.replace('sqlite:///', ''))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        # Crear engine
        self.engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True  # Verificar conexiones antes de usar
        )

        # Crear session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Crear tablas
        self.create_tables()

        self.logger.info(f"Base de datos inicializada: {db_url}")

    def create_tables(self):
        """Crea todas las tablas si no existen"""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Tablas de base de datos verificadas/creadas")
        except Exception as e:
            self.logger.error(f"Error creando tablas: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager para sesiones de base de datos

        Usage:
            with db.get_session() as session:
                job = session.query(PrintJob).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error en sesión de BD: {e}")
            raise
        finally:
            session.close()

    # === Print Jobs ===

    def create_print_job(self, job_data: Dict[str, Any]) -> PrintJob:
        """
        Crea un nuevo trabajo de impresión

        Args:
            job_data: Diccionario con los datos del trabajo

        Returns:
            Trabajo de impresión creado
        """
        with self.get_session() as session:
            job = PrintJob(**job_data)
            session.add(job)
            session.flush()  # Para obtener el ID
            self.logger.info(f"Trabajo creado en BD: {job.job_id}")
            return job

    def get_print_job(self, job_id: str) -> Optional[PrintJob]:
        """Obtiene un trabajo por su job_id"""
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(job_id=job_id).first()

    def get_print_job_by_id(self, id: int) -> Optional[PrintJob]:
        """Obtiene un trabajo por su ID numérico"""
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(id=id).first()

    def update_print_job(
        self,
        job_id: str,
        updates: Dict[str, Any]
    ) -> Optional[PrintJob]:
        """
        Actualiza un trabajo de impresión

        Args:
            job_id: ID del trabajo
            updates: Diccionario con campos a actualizar

        Returns:
            Trabajo actualizado o None
        """
        with self.get_session() as session:
            job = session.query(PrintJob).filter_by(job_id=job_id).first()
            if job:
                for key, value in updates.items():
                    setattr(job, key, value)
                session.flush()
                self.logger.debug(f"Trabajo actualizado: {job_id}")
            return job

    def get_pending_jobs(self, limit: int = 100) -> List[PrintJob]:
        """
        Obtiene trabajos pendientes ordenados por prioridad

        Args:
            limit: Número máximo de trabajos a retornar

        Returns:
            Lista de trabajos pendientes
        """
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(
                status='pending'
            ).order_by(
                PrintJob.priority.asc(),
                PrintJob.created_at.asc()
            ).limit(limit).all()

    def get_next_print_job(self) -> Optional[PrintJob]:
        """Obtiene el siguiente trabajo a procesar (mayor prioridad)"""
        jobs = self.get_pending_jobs(limit=1)
        return jobs[0] if jobs else None

    def get_jobs_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[PrintJob]:
        """Obtiene trabajos filtrados por estado"""
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(
                status=status
            ).order_by(
                PrintJob.created_at.desc()
            ).limit(limit).offset(offset).all()

    def get_jobs_by_user(
        self,
        user_name: str,
        limit: int = 100
    ) -> List[PrintJob]:
        """Obtiene trabajos de un usuario específico"""
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(
                user_name=user_name
            ).order_by(
                PrintJob.created_at.desc()
            ).limit(limit).all()

    def get_recent_jobs(self, limit: int = 50) -> List[PrintJob]:
        """Obtiene los trabajos más recientes"""
        with self.get_session() as session:
            return session.query(PrintJob).order_by(
                PrintJob.created_at.desc()
            ).limit(limit).all()

    def delete_print_job(self, job_id: str) -> bool:
        """
        Elimina un trabajo de impresión

        Args:
            job_id: ID del trabajo

        Returns:
            True si se eliminó, False si no existía
        """
        with self.get_session() as session:
            job = session.query(PrintJob).filter_by(job_id=job_id).first()
            if job:
                session.delete(job)
                self.logger.info(f"Trabajo eliminado: {job_id}")
                return True
            return False

    def count_jobs_by_status(self, status: str) -> int:
        """Cuenta trabajos por estado"""
        with self.get_session() as session:
            return session.query(PrintJob).filter_by(status=status).count()

    # === Clients ===

    def create_or_update_client(
        self,
        client_id: str,
        ip_address: str,
        hostname: Optional[str] = None
    ) -> Client:
        """Crea o actualiza un cliente"""
        with self.get_session() as session:
            client = session.query(Client).filter_by(client_id=client_id).first()

            if client:
                # Actualizar existente
                client.ip_address = ip_address
                client.hostname = hostname or client.hostname
                client.last_seen = datetime.utcnow()
                client.is_active = True
            else:
                # Crear nuevo
                client = Client(
                    client_id=client_id,
                    ip_address=ip_address,
                    hostname=hostname,
                    last_seen=datetime.utcnow()
                )
                session.add(client)

            session.flush()
            return client

    def get_client(self, client_id: str) -> Optional[Client]:
        """Obtiene un cliente por su ID"""
        with self.get_session() as session:
            return session.query(Client).filter_by(client_id=client_id).first()

    def get_all_clients(self) -> List[Client]:
        """Obtiene todos los clientes"""
        with self.get_session() as session:
            return session.query(Client).all()

    def increment_client_stats(
        self,
        client_id: str,
        jobs: int = 1,
        pages: int = 0
    ):
        """Incrementa las estadísticas de un cliente"""
        with self.get_session() as session:
            client = session.query(Client).filter_by(client_id=client_id).first()
            if client:
                client.total_jobs += jobs
                client.total_pages += pages

    # === Server Stats ===

    def get_or_create_stats(self, date_obj: date) -> ServerStats:
        """Obtiene o crea estadísticas para una fecha"""
        with self.get_session() as session:
            stats = session.query(ServerStats).filter_by(
                date=datetime.combine(date_obj, datetime.min.time())
            ).first()

            if not stats:
                stats = ServerStats(
                    date=datetime.combine(date_obj, datetime.min.time())
                )
                session.add(stats)
                session.flush()

            return stats

    def update_stats(self, updates: Dict[str, Any]):
        """Actualiza las estadísticas del día actual"""
        today = date.today()
        with self.get_session() as session:
            stats = session.query(ServerStats).filter_by(
                date=datetime.combine(today, datetime.min.time())
            ).first()

            if not stats:
                stats = ServerStats(
                    date=datetime.combine(today, datetime.min.time()),
                    **updates
                )
                session.add(stats)
            else:
                for key, value in updates.items():
                    setattr(stats, key, value)

    def get_stats_by_date(self, date_obj: date) -> Optional[ServerStats]:
        """Obtiene estadísticas de una fecha específica"""
        with self.get_session() as session:
            return session.query(ServerStats).filter_by(
                date=datetime.combine(date_obj, datetime.min.time())
            ).first()

    def get_stats_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[ServerStats]:
        """Obtiene estadísticas de un rango de fechas"""
        with self.get_session() as session:
            return session.query(ServerStats).filter(
                ServerStats.date >= datetime.combine(start_date, datetime.min.time()),
                ServerStats.date <= datetime.combine(end_date, datetime.max.time())
            ).order_by(ServerStats.date.asc()).all()

    # === Summary and Analytics ===

    def get_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen general del sistema"""
        with self.get_session() as session:
            total_jobs = session.query(PrintJob).count()
            pending_jobs = self.count_jobs_by_status('pending')
            printing_jobs = self.count_jobs_by_status('printing')
            completed_jobs = self.count_jobs_by_status('completed')
            failed_jobs = self.count_jobs_by_status('failed')

            total_pages = session.query(func.sum(PrintJob.page_count)).scalar() or 0
            total_clients = session.query(Client).count()
            active_clients = session.query(Client).filter_by(is_active=True).count()

            return {
                'total_jobs': total_jobs,
                'pending_jobs': pending_jobs,
                'printing_jobs': printing_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'total_pages': total_pages,
                'total_clients': total_clients,
                'active_clients': active_clients
            }

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Elimina trabajos completados más antiguos que X días

        Args:
            days: Días de retención

        Returns:
            Número de trabajos eliminados
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            deleted = session.query(PrintJob).filter(
                PrintJob.status.in_(['completed', 'failed', 'cancelled']),
                PrintJob.completed_at < cutoff_date
            ).delete()

            self.logger.info(f"Eliminados {deleted} trabajos antiguos")
            return deleted

    # ========================================================================
    # Gestión de Usuarios
    # ========================================================================

    def create_user(
        self,
        username: str,
        password_hash: str,
        password_salt: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = 'user'
    ) -> User:
        """
        Crea un nuevo usuario

        Args:
            username: Nombre de usuario
            password_hash: Hash de la contraseña
            password_salt: Salt de la contraseña
            email: Email (opcional)
            full_name: Nombre completo (opcional)
            role: Rol del usuario (admin, user, viewer)

        Returns:
            Usuario creado
        """
        with self.get_session() as session:
            user = User(
                username=username,
                password_hash=password_hash,
                password_salt=password_salt,
                email=email,
                full_name=full_name,
                role=role
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            self.logger.info(f"Usuario creado: {username} (role={role})")
            return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por su username"""
        with self.get_session() as session:
            return session.query(User).filter(
                User.username == username
            ).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene un usuario por su ID"""
        with self.get_session() as session:
            return session.query(User).filter(
                User.id == user_id
            ).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por su email"""
        with self.get_session() as session:
            return session.query(User).filter(
                User.email == email
            ).first()

    def get_all_users(self, active_only: bool = False) -> List[User]:
        """
        Obtiene todos los usuarios

        Args:
            active_only: Solo usuarios activos

        Returns:
            Lista de usuarios
        """
        with self.get_session() as session:
            query = session.query(User)

            if active_only:
                query = query.filter(User.is_active == True)

            return query.order_by(User.username).all()

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None
    ) -> Optional[User]:
        """
        Actualiza un usuario

        Args:
            user_id: ID del usuario
            email: Nuevo email (opcional)
            full_name: Nuevo nombre completo (opcional)
            role: Nuevo rol (opcional)
            is_active: Nuevo estado activo (opcional)
            is_verified: Nuevo estado verificado (opcional)

        Returns:
            Usuario actualizado o None si no existe
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return None

            if email is not None:
                user.email = email
            if full_name is not None:
                user.full_name = full_name
            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active
            if is_verified is not None:
                user.is_verified = is_verified

            session.commit()
            session.refresh(user)

            self.logger.info(f"Usuario actualizado: {user.username}")
            return user

    def update_user_password(
        self,
        user_id: int,
        password_hash: str,
        password_salt: str
    ) -> bool:
        """
        Actualiza la contraseña de un usuario

        Args:
            user_id: ID del usuario
            password_hash: Nuevo hash de contraseña
            password_salt: Nuevo salt

        Returns:
            True si se actualizó, False si no
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return False

            user.password_hash = password_hash
            user.password_salt = password_salt

            session.commit()

            self.logger.info(f"Contraseña actualizada para: {user.username}")
            return True

    def update_user_last_login(self, user_id: int):
        """Actualiza el timestamp de último login"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if user:
                user.last_login = datetime.utcnow()
                session.commit()

    def update_user_last_activity(self, user_id: int):
        """Actualiza el timestamp de última actividad"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if user:
                user.last_activity = datetime.utcnow()
                session.commit()

    def delete_user(self, user_id: int) -> bool:
        """
        Elimina un usuario

        Args:
            user_id: ID del usuario

        Returns:
            True si se eliminó, False si no
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return False

            username = user.username
            session.delete(user)
            session.commit()

            self.logger.info(f"Usuario eliminado: {username}")
            return True

    def get_users_by_role(self, role: str) -> List[User]:
        """Obtiene todos los usuarios con un rol específico"""
        with self.get_session() as session:
            return session.query(User).filter(
                User.role == role,
                User.is_active == True
            ).all()


# Alias para compatibilidad
DatabaseManager = Database
