# Fase 5: Interfaces de Usuario - Documentación

## Visión General

La Fase 5 implementa interfaces de usuario para gestión y monitoreo del sistema:

- **API REST**: Endpoints completos con FastAPI
- **Dashboard Web**: Interfaz web para monitoreo y gestión
- **Gestión de Usuarios**: Sistema completo de usuarios con roles
- **Autenticación**: Login con JWT integrado

## Estado: ✅ Completado

---

## Componentes Implementados

### 1. **Sistema de Gestión de Usuarios**

#### Modelo de Usuario (`server/database/models.py`)

```python
class User(Base):
    username = Column(String(50), unique=True)
    password_hash = Column(String(255))
    password_salt = Column(String(255))
    email = Column(String(100))
    full_name = Column(String(100))
    role = Column(String(20))  # admin, user, viewer
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    last_login = Column(DateTime)
```

#### Roles

- **admin**: Acceso completo a todo el sistema
- **user**: Puede ver sus propios trabajos y estadísticas
- **viewer**: Solo lectura de trabajos y estadísticas

#### Operaciones de Base de Datos

```python
# Crear usuario
user = db_manager.create_user(
    username='john',
    password_hash=hash_hex,
    password_salt=salt,
    role='user'
)

# Obtener usuario
user = db_manager.get_user_by_username('john')

# Actualizar usuario
db_manager.update_user(user.id, role='admin')

# Eliminar usuario
db_manager.delete_user(user.id)
```

---

### 2. **API REST con FastAPI**

#### Servidor API (`server/api/main.py`)

API completa con autenticación JWT y autorización basada en roles.

#### Endpoints de Autenticación

**POST /api/auth/login**
```json
{
  "username": "admin",
  "password": "password"
}
```

Respuesta:
```json
{
  "token": "eyJhbGc...",
  "user": {...},
  "expires_in": 86400
}
```

**POST /api/auth/refresh**
```
Headers: Authorization: Bearer <token>
```

#### Endpoints de Usuarios

- **GET /api/users** - Lista usuarios (admin)
- **GET /api/users/me** - Info del usuario actual
- **GET /api/users/{id}** - Usuario específico (admin)
- **POST /api/users** - Crear usuario (admin)
- **PUT /api/users/{id}** - Actualizar usuario (admin)
- **DELETE /api/users/{id}** - Eliminar usuario (admin)

#### Endpoints de Trabajos

- **GET /api/jobs** - Lista trabajos
- **GET /api/jobs/{job_id}** - Trabajo específico

#### Endpoints de Estadísticas

- **GET /api/stats** - Estadísticas generales
- **GET /api/stats/clients** - Stats por cliente (admin)

#### Health Check

- **GET /api/health** - Estado del servidor

#### Autenticación

Todos los endpoints (excepto /api/auth/login y /api/health) requieren JWT token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/jobs
```

---

### 3. **Dashboard Web**

#### Interfaz (`server/web/templates/dashboard.html`)

Dashboard web completo con:
- ✅ Login con autenticación JWT
- ✅ Estadísticas en tiempo real
- ✅ Lista de trabajos de impresión
- ✅ Diseño responsive
- ✅ Auto-refresh cada 30 segundos
- ✅ Gestión de sesión con localStorage

#### Funcionalidades

**Login**:
- Formulario de autenticación
- Validación de credenciales
- Almacenamiento seguro de token

**Dashboard**:
- Estadísticas: Total trabajos, completados, pendientes, fallidos
- Tabla de trabajos con estado visual
- Información del usuario
- Logout

---

## Instalación y Uso

### 1. **Instalar Dependencias**

```bash
cd server
pip install -r requirements.txt
```

Dependencias añadidas:
- `fastapi>=0.104.1`
- `uvicorn[standard]>=0.24.0`

### 2. **Crear Usuario Administrador**

```bash
python scripts/create_admin_user.py
```

Este script:
- Crea usuario admin inicial
- Permite cambiar contraseña de admin existente
- Genera hash seguro de contraseña

### 3. **Iniciar Servidor API**

```bash
python server/api_server.py --port 8080
```

Opciones:
- `--host`: Host para escuchar (default: 0.0.0.0)
- `--port`: Puerto (default: 8080)
- `--reload`: Auto-reload en cambios (desarrollo)
- `--log-level`: Nivel de logging

### 4. **Acceder al Dashboard**

Abrir en navegador:
- Dashboard: http://localhost:8080/
- Documentación API (Swagger): http://localhost:8080/docs
- Documentación API (ReDoc): http://localhost:8080/redoc

---

## Ejemplos de Uso

### API con cURL

**Login:**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Obtener estadísticas:**
```bash
TOKEN="<tu_token>"
curl http://localhost:8080/api/stats \
  -H "Authorization: Bearer $TOKEN"
```

**Crear usuario:**
```bash
curl -X POST http://localhost:8080/api/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "password123",
    "email": "john@example.com",
    "role": "user"
  }'
```

---

## Seguridad

### Autenticación JWT

- Tokens firmados con secret key configurablesmart
- Expiración configurable (default: 24h)
- Refresh de tokens disponible
- Validación en cada request

### Autorización Basada en Roles

```python
# Solo admin puede acceder
@app.get("/api/users")
async def list_users(
    current_user: dict = Depends(require_role('admin'))
):
    ...
```

### Rate Limiting

Integrado con el sistema de seguridad de Fase 4.

### Validación de Inputs

Pydantic schemas validan todos los inputs:
```python
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(default='user', regex='^(admin|user|viewer)$')
```

---

## Estructura de Archivos

```
server/
├── api/
│   ├── __init__.py
│   └── main.py              # API FastAPI
├── web/
│   ├── static/              # Archivos estáticos (CSS, JS)
│   └── templates/
│       └── dashboard.html   # Dashboard web
├── database/
│   ├── models.py            # Modelo User añadido
│   └── database.py          # Métodos de gestión de usuarios
└── api_server.py            # Script para ejecutar API

scripts/
└── create_admin_user.py     # Crear usuario admin inicial
```

---

## Testing

### Test Manual de la API

1. Iniciar servidor:
```bash
python server/api_server.py
```

2. Crear usuario admin:
```bash
python scripts/create_admin_user.py
```

3. Probar login:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"tu_password"}'
```

4. Verificar health check:
```bash
curl http://localhost:8080/api/health
```

### Test del Dashboard

1. Abrir http://localhost:8080/
2. Login con credenciales de admin
3. Verificar estadísticas
4. Verificar lista de trabajos
5. Probar logout

---

## Configuración

### Configurar Secret Key

En `server/api/main.py`, cambiar:
```python
auth_manager = AuthenticationManager(
    secret_key='your_secret_key_here',  # <-- Cambiar esto
    token_expiration_hours=24
)
```

Generar secret key seguro:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Configurar Base de Datos

Por defecto usa SQLite en `./data/printer_connect.db`.

Para PostgreSQL:
```python
db_manager = DatabaseManager(
    'postgresql://user:password@localhost/printer_connect',
    logger=logger
)
```

---

## Características Destacadas

✅ **API REST Completa** con FastAPI
✅ **Autenticación JWT** integrada
✅ **Gestión de Usuarios** con roles y permisos
✅ **Dashboard Web** responsive y moderno
✅ **Documentación Interactiva** (Swagger/ReDoc)
✅ **Auto-refresh** de datos en dashboard
✅ **Seguridad** integrada con Fase 4
✅ **Rate Limiting** por usuario
✅ **Validación** exhaustiva de inputs

---

## Próximos Pasos

La Fase 5 establece la base de interfaces. Las siguientes fases incluirán:

**Fase 6: Testing y Optimización**
- Tests de la API
- Tests de carga
- Optimización de queries

**Fase 7: Deployment**
- Instaladores completos
- Servicios de sistema
- Monitoreo con Prometheus

---

## Referencias

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Uvicorn](https://www.uvicorn.org/)
- [JWT.io](https://jwt.io/)

---

**Última actualización:** 2025-11-07
**Versión:** 0.5.0
**Estado:** ✅ Completado
