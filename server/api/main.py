"""
API REST para Printer_connect usando FastAPI
Provee endpoints para gestión de trabajos, usuarios y estadísticas
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import logging

from server.database.database import DatabaseManager
from shared.security.auth import AuthenticationManager, TokenValidator, AuthenticationError
from shared.security.validation import InputValidator, ValidationError
from shared.security.rate_limiter import RateLimiter


# Esquemas Pydantic
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    token: str
    user: dict
    expires_in: int


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = Field(default='user', regex='^(admin|user|viewer)$')


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, regex='^(admin|user|viewer)$')
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


class JobListResponse(BaseModel):
    total: int
    jobs: List[dict]


class StatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    total_pages: int
    total_clients: int
    active_clients: int


# Aplicación FastAPI
app = FastAPI(
    title="Printer_connect API",
    description="API REST para gestión de sistema de impresión",
    version="0.5.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seguridad
security = HTTPBearer()

# Variables globales (se inicializan en startup)
db_manager: Optional[DatabaseManager] = None
auth_manager: Optional[AuthenticationManager] = None
token_validator: Optional[TokenValidator] = None
rate_limiter: Optional[RateLimiter] = None
input_validator: Optional[InputValidator] = None
logger: Optional[logging.Logger] = None


@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar"""
    global db_manager, auth_manager, token_validator, rate_limiter, input_validator, logger

    logger = logging.getLogger(__name__)

    # Base de datos
    db_manager = DatabaseManager('sqlite:///./data/printer_connect.db', logger=logger)

    # Autenticación
    auth_manager = AuthenticationManager(
        secret_key='your_secret_key_here',  # Cargar desde config
        token_expiration_hours=24,
        logger=logger
    )

    token_validator = TokenValidator(auth_manager, logger=logger)

    # Rate limiting
    rate_limiter = RateLimiter(
        requests_per_minute=60,
        logger=logger
    )

    # Validación
    input_validator = InputValidator(logger=logger)

    logger.info("API REST inicializada")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependencia para obtener el usuario actual desde el token

    Args:
        credentials: Credenciales HTTP Bearer

    Returns:
        Dictionary con información del usuario

    Raises:
        HTTPException: Si el token es inválido
    """
    token = credentials.credentials

    try:
        payload = token_validator.validate(token)
        return payload

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_role(required_role: str):
    """
    Dependencia para verificar roles

    Args:
        required_role: Rol requerido (admin, user, viewer)

    Returns:
        Function que verifica el rol del usuario
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get('role', 'user')

        # Admin tiene acceso a todo
        if user_role == 'admin':
            return current_user

        # Verificar rol específico
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{required_role}' requerido"
            )

        return current_user

    return role_checker


# ========================================================================
# Endpoints de Autenticación
# ========================================================================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Autentica un usuario y retorna un token JWT

    Args:
        request: Credenciales de login

    Returns:
        Token JWT y información del usuario
    """
    try:
        # Buscar usuario
        user = db_manager.get_user_by_username(request.username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        # Verificar contraseña
        is_valid = AuthenticationManager.verify_password(
            request.password,
            user.password_hash,
            bytes.fromhex(user.password_salt)
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        # Verificar que el usuario esté activo
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        # Generar token
        token = auth_manager.generate_token(
            client_id=str(user.id),
            username=user.username,
            roles=[user.role]
        )

        # Actualizar último login
        db_manager.update_user_last_login(user.id)

        return LoginResponse(
            token=token,
            user=user.to_dict(),
            expires_in=auth_manager.token_expiration_hours * 3600
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@app.post("/api/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Renueva un token JWT"""
    user_id = int(current_user['client_id'])
    user = db_manager.get_user_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido"
        )

    new_token = auth_manager.generate_token(
        client_id=str(user.id),
        username=user.username,
        roles=[user.role]
    )

    return {"token": new_token}


# ========================================================================
# Endpoints de Usuarios
# ========================================================================

@app.get("/api/users", response_model=List[UserResponse])
async def list_users(
    active_only: bool = False,
    current_user: dict = Depends(require_role('admin'))
):
    """Lista todos los usuarios (solo admin)"""
    users = db_manager.get_all_users(active_only=active_only)
    return [UserResponse(**user.to_dict()) for user in users]


@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Obtiene información del usuario actual"""
    user_id = int(current_user['client_id'])
    user = db_manager.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return UserResponse(**user.to_dict())


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(require_role('admin'))
):
    """Obtiene un usuario por ID (solo admin)"""
    user = db_manager.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return UserResponse(**user.to_dict())


@app.post("/api/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_role('admin'))
):
    """Crea un nuevo usuario (solo admin)"""
    # Verificar que no exista
    existing = db_manager.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )

    # Hash de contraseña
    password_hash, password_salt = AuthenticationManager.hash_password(user_data.password)

    # Crear usuario
    user = db_manager.create_user(
        username=user_data.username,
        password_hash=password_hash,
        password_salt=password_salt.hex(),
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role
    )

    return UserResponse(**user.to_dict())


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(require_role('admin'))
):
    """Actualiza un usuario (solo admin)"""
    user = db_manager.update_user(
        user_id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return UserResponse(**user.to_dict())


@app.delete("/api/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_role('admin'))
):
    """Elimina un usuario (solo admin)"""
    success = db_manager.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return None


# ========================================================================
# Endpoints de Trabajos de Impresión
# ========================================================================

@app.get("/api/jobs", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Lista trabajos de impresión"""
    # Users solo ven sus propios trabajos
    user_role = current_user.get('role', 'user')
    if user_role != 'admin' and user_role != 'viewer':
        client_id = current_user['client_id']

    jobs = db_manager.get_print_jobs(
        status=status_filter,
        client_id=client_id,
        limit=limit,
        offset=offset
    )

    return JobListResponse(
        total=len(jobs),
        jobs=[job.to_dict() for job in jobs]
    )


@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtiene un trabajo específico"""
    job = db_manager.get_print_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")

    # Verificar permisos
    user_role = current_user.get('role', 'user')
    if user_role not in ['admin', 'viewer']:
        if job.client_id != current_user['client_id']:
            raise HTTPException(status_code=403, detail="Acceso denegado")

    return job.to_dict()


# ========================================================================
# Endpoints de Estadísticas
# ========================================================================

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Obtiene estadísticas generales"""
    stats = db_manager.get_summary()
    return StatsResponse(**stats)


@app.get("/api/stats/clients")
async def get_client_stats(current_user: dict = Depends(require_role('admin'))):
    """Obtiene estadísticas por cliente (solo admin)"""
    clients = db_manager.get_all_clients()
    return [client.to_dict() for client in clients]


# ========================================================================
# Endpoint de Health Check
# ========================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.5.0"
    }


# ========================================================================
# Servir Dashboard Web
# ========================================================================

# Montar archivos estáticos
static_dir = Path(__file__).parent.parent / 'web' / 'static'
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Sirve el dashboard web"""
    html_file = Path(__file__).parent.parent / 'web' / 'templates' / 'dashboard.html'

    if html_file.exists():
        return FileResponse(html_file)
    else:
        return HTMLResponse(content="""
            <html>
                <head><title>Printer_connect</title></head>
                <body>
                    <h1>Printer_connect API</h1>
                    <p>API REST está funcionando</p>
                    <p><a href="/docs">Documentación de API</a></p>
                </body>
            </html>
        """)
