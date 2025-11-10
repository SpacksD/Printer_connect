# Fase 4: Seguridad - Documentación

## Visión General

La Fase 4 implementa un sistema completo de seguridad para Printer_connect, incluyendo:

- **TLS/SSL**: Encriptación de comunicaciones
- **Autenticación JWT**: Tokens de autenticación seguros
- **Validación de Inputs**: Prevención de ataques de inyección
- **Rate Limiting**: Protección contra abuso y DoS
- **Logs de Auditoría**: Registro de eventos de seguridad

## Estado: ✅ Completado

---

## Características Implementadas

### 1. TLS/SSL

#### Descripción
Sistema completo de encriptación de comunicaciones usando TLS 1.2+.

#### Componentes

**`shared/security/tls_wrapper.py`**
- `TLSSocketWrapper`: Wrapper para sockets TLS
- `create_tls_context()`: Creación de contextos SSL
- `create_server_context()`: Contexto para servidor
- `create_client_context()`: Contexto para cliente

**Características**:
- Soporte TLS 1.2 y 1.3
- Deshabilitado SSLv2, SSLv3, TLS 1.0, TLS 1.1
- Verificación de certificados configurable
- Soporte para autenticación mutua (opcional)

#### Generación de Certificados

```bash
# Generar certificado de servidor
python scripts/generate_certificates.py --server --hostname localhost

# Generar certificados de servidor y cliente
python scripts/generate_certificates.py --all --hostname myserver.local

# Especificar días de validez
python scripts/generate_certificates.py --server --days 730
```

**Archivos generados**:
- `certs/server.crt` - Certificado del servidor
- `certs/server.key` - Clave privada del servidor
- `certs/client.crt` - Certificado del cliente (opcional)
- `certs/client.key` - Clave privada del cliente (opcional)

⚠️ **IMPORTANTE**: Los certificados generados son autofirmados. Para producción, usa certificados de una CA reconocida.

---

### 2. Autenticación JWT

#### Descripción
Sistema de autenticación basado en JSON Web Tokens (JWT).

#### Componentes

**`shared/security/auth.py`**
- `AuthenticationManager`: Gestión de tokens y contraseñas
- `TokenValidator`: Validación de tokens
- `hash_password()`: Hash de contraseñas con PBKDF2-SHA256
- `verify_password()`: Verificación de contraseñas

#### Uso

**Generar Token:**

```python
from shared.security.auth import AuthenticationManager

auth_manager = AuthenticationManager(
    secret_key='your_secret_key_here',
    token_expiration_hours=24
)

token = auth_manager.generate_token(
    client_id='client_123',
    username='john_doe',
    roles=['user', 'print']
)
```

**Validar Token:**

```python
try:
    payload = auth_manager.validate_token(token)
    print(f"Token válido para: {payload['client_id']}")
except TokenExpiredError:
    print("Token expirado")
except TokenInvalidError:
    print("Token inválido")
```

**Hash de Contraseñas:**

```python
# Generar hash
password = 'my_password'
hash_hex, salt = AuthenticationManager.hash_password(password)

# Verificar contraseña
is_valid = AuthenticationManager.verify_password(
    password, hash_hex, salt
)
```

#### Configuración

En `server/config.ini`:

```ini
[Security]
# Secret key para firmar tokens (CAMBIAR EN PRODUCCIÓN)
jwt_secret_key = your_secret_key_here

# Expiración de tokens en horas
token_expiration_hours = 24
```

**Generar secret key seguro:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 3. Validación de Inputs

#### Descripción
Validación exhaustiva de todos los inputs para prevenir ataques.

#### Componentes

**`shared/security/validation.py`**
- `InputValidator`: Validador de inputs
- `ValidationError`: Excepción de validación

#### Validaciones Disponibles

**Client ID:**
```python
validator = InputValidator()
client_id = validator.validate_client_id('client_123')
# Solo: a-z, A-Z, 0-9, _, -
# Longitud: 1-100 caracteres
```

**Username:**
```python
username = validator.validate_username('john_doe')
# Solo: a-z, A-Z, 0-9, _, ., -
# Longitud: 3-50 caracteres
```

**Archivo:**
```python
file_path = Path('document.pdf')
validated_path = validator.validate_file_path(file_path)
# Verifica:
# - Existe
# - Es archivo (no directorio)
# - Extensión permitida
# - Tamaño dentro del límite
# - No hay path traversal
```

**String Genérico:**
```python
value = validator.validate_string(
    "some value",
    field_name="description",
    min_length=5,
    max_length=100
)
```

**Entero:**
```python
value = validator.validate_integer(
    10,
    field_name="priority",
    min_value=1,
    max_value=10
)
```

**Enum:**
```python
value = validator.validate_enum(
    "option1",
    allowed_values=['option1', 'option2', 'option3']
)
```

#### Configuración

```ini
[Security]
# Tamaño máximo de archivo en MB
max_file_size_mb = 100

# Extensiones permitidas (separadas por comas)
allowed_file_extensions = .pdf,.ps
```

---

### 4. Rate Limiting

#### Descripción
Protección contra abuso y ataques DoS usando algoritmo Token Bucket.

#### Componentes

**`shared/security/rate_limiter.py`**
- `RateLimiter`: Rate limiter básico
- `AdaptiveRateLimiter`: Rate limiter adaptativo
- `TokenBucket`: Implementación de token bucket

#### Uso

**Básico:**

```python
from shared.security.rate_limiter import RateLimiter

limiter = RateLimiter(
    requests_per_minute=60,
    burst_size=10
)

# Verificar si el cliente puede hacer una request
try:
    limiter.check_rate_limit('client_123')
    # Request permitida
except RateLimitExceeded as e:
    print(f"Rate limit excedido: {e}")
```

**Sin Excepción:**

```python
if limiter.check_rate_limit('client_123', raise_on_limit=False):
    # Procesar request
    pass
else:
    # Rate limit excedido
    pass
```

**Obtener Información:**

```python
# Requests restantes
remaining = limiter.get_remaining_requests('client_123')

# Tiempo de espera
wait_time = limiter.get_wait_time('client_123')

# Resetear cliente
limiter.reset_client('client_123')

# Estadísticas
stats = limiter.get_stats()
```

#### Configuración

```ini
[Security]
# Habilitar rate limiting
enable_rate_limiting = true

# Requests permitidos por minuto
requests_per_minute = 60
```

---

## Servidor Seguro

### Componentes

**`server/network/server_v4.py`**
- `SecurePrintServer`: Servidor con TLS y autenticación

**`server/main_v4.py`**
- Punto de entrada del servidor seguro

### Configuración

**`server/config.ini`:**

```ini
[Server]
host = 0.0.0.0
port = 9100

[Security]
# TLS/SSL
tls_enabled = true
cert_dir = certs
certfile = server.crt
keyfile = server.key

# Autenticación JWT
require_authentication = true
jwt_secret_key = CHANGE_THIS_SECRET_KEY
token_expiration_hours = 24

# Rate Limiting
enable_rate_limiting = true
requests_per_minute = 60

# Validación
max_file_size_mb = 100
allowed_file_extensions = .pdf,.ps
```

### Iniciar Servidor

```bash
# 1. Generar certificados (primera vez)
python scripts/generate_certificates.py --server

# 2. Configurar server/config.ini
cp server/config.ini.example server/config.ini
# Editar config.ini y cambiar jwt_secret_key

# 3. Iniciar servidor
python server/main_v4.py
```

El servidor imprimirá un token de ejemplo para testing.

---

## Cliente Seguro

### Componentes

**`client/network/secure_client.py`**
- `SecurePrintClient`: Cliente con TLS y autenticación
- `ClientAuthenticator`: Ayudante para autenticación

### Configuración

**`client/config.ini`:**

```ini
[Server]
host = 192.168.1.100
port = 9100

[Security]
# TLS/SSL
tls_enabled = true
cert_dir = certs
cafile = server.crt  # Certificado del servidor
verify_server = true

[Authentication]
username = john_doe
# auth_token =  # Se configura programáticamente
```

### Uso

```python
from pathlib import Path
from client.network.secure_client import SecurePrintClient
from shared.data_models import PrintParameters, PrintJobMetadata

# Crear cliente
client = SecurePrintClient(
    server_host='192.168.1.100',
    server_port=9100,
    client_id='my_client',
    cafile=Path('certs/server.crt'),
    verify_server=True
)

# Configurar token (obtenido del servidor)
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
client.set_auth_token(token)

# Probar conexión
if client.test_connection():
    print("✓ Conexión exitosa")

# Enviar trabajo de impresión
response = client.send_print_job(
    user='john_doe',
    file_path=Path('document.pdf'),
    parameters=PrintParameters(),
    metadata=PrintJobMetadata(document_name='My Document')
)

print(f"Job ID: {response['data']['job_id']}")
```

---

## Testing

### Tests Unitarios

```bash
# Ejecutar todos los tests de seguridad
pytest tests/test_security.py -v

# Tests específicos
pytest tests/test_security.py::TestInputValidator -v
pytest tests/test_security.py::TestRateLimiter -v
pytest tests/test_security.py::TestAuthenticationManager -v
```

### Test End-to-End

```bash
# Test completo de Fase 4
python scripts/test_phase4.py
```

Tests incluidos:
1. Verificación de certificados
2. Authentication Manager
3. Input Validator
4. Rate Limiter
5. TLS Context Creation

---

## Arquitectura de Seguridad

### Flujo de Autenticación

```
1. Cliente solicita token (fuera de banda o endpoint dedicado)
2. Servidor genera JWT con claims
3. Cliente guarda token
4. Cliente incluye token en cada request (header Authorization)
5. Servidor valida token antes de procesar request
6. Si token válido: procesar request
7. Si token inválido/expirado: rechazar con 401 Unauthorized
```

### Flujo de Conexión TLS

```
1. Cliente inicia conexión TCP
2. Cliente inicia handshake TLS
3. Servidor presenta certificado
4. Cliente verifica certificado (opcional)
5. Se establece canal encriptado
6. Intercambio de mensajes sobre canal seguro
```

### Capas de Seguridad

```
┌─────────────────────────────────────┐
│  Logs de Auditoría                  │
├─────────────────────────────────────┤
│  Rate Limiting                      │
├─────────────────────────────────────┤
│  Validación de Inputs               │
├─────────────────────────────────────┤
│  Autenticación JWT                  │
├─────────────────────────────────────┤
│  Encriptación TLS/SSL               │
└─────────────────────────────────────┘
```

---

## Mejores Prácticas

### Producción

1. **Certificados**
   - Usar certificados de CA reconocida (Let's Encrypt, etc.)
   - Renovar certificados antes de expiración
   - No commitear claves privadas en git

2. **Secret Keys**
   - Generar secret key criptográficamente seguro
   - Cambiar en cada ambiente (dev/staging/prod)
   - No hardcodear en código
   - Usar variables de entorno o vault

3. **Tokens**
   - Expiración razonable (24h máximo)
   - Implementar refresh de tokens
   - Revocar tokens comprometidos
   - No loggear tokens completos

4. **Rate Limiting**
   - Ajustar según capacidad del servidor
   - Diferentes límites por tipo de operación
   - Whitelist para clientes confiables

5. **Validación**
   - Validar TODOS los inputs
   - Sanitizar antes de usar
   - Límites estrictos de tamaño
   - Whitelist de extensiones

### Desarrollo

1. **Certificados Autofirmados**
   - OK para desarrollo y testing
   - Deshabilitar verificación si es necesario
   - Generar nuevos periódicamente

2. **Secret Keys**
   - Usar claves de prueba
   - Documentar claramente como "testing"

3. **Logging**
   - Nivel DEBUG OK
   - No loggear información sensible
   - Rotar logs frecuentemente

---

## Troubleshooting

### Error: "Certificado no encontrado"

```bash
# Generar certificados
python scripts/generate_certificates.py --server --hostname localhost
```

### Error: "Token inválido"

- Verificar que el token es correcto
- Verificar que no ha expirado
- Verificar que el secret_key es el mismo en cliente y servidor

### Error: "SSL handshake failed"

- Verificar que TLS está habilitado en ambos lados
- Verificar rutas de certificados
- Para testing: deshabilitar verificación del servidor

### Error: "Rate limit exceeded"

- Esperar el tiempo indicado
- Resetear cliente si es necesario
- Ajustar límites en configuración

---

## Próximos Pasos

La Fase 4 establece la base de seguridad. Las siguientes fases incluirán:

**Fase 5: Interfaces de Usuario**
- Login UI para clientes
- Dashboard de administración
- Gestión de usuarios y tokens

**Fase 6: Testing y Optimización**
- Tests de penetración
- Auditoría de seguridad
- Optimización de rendimiento

**Fase 7: Deployment**
- Scripts de instalación seguros
- Configuración de firewall
- Monitoreo de seguridad

---

## Referencias

- [JWT.io](https://jwt.io/) - JSON Web Tokens
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Vulnerabilidades comunes
- [Python ssl](https://docs.python.org/3/library/ssl.html) - Documentación SSL
- [PyJWT](https://pyjwt.readthedocs.io/) - Documentación PyJWT
- [Cryptography](https://cryptography.io/) - Documentación cryptography

---

**Última actualización:** 2025-11-07
**Versión:** 0.4.0
**Estado:** ✅ Completado
