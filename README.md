# Printer_connect

Sistema Cliente/Servidor de impresión en red local que soluciona problemas de configuración de impresoras en entornos Windows con dominio.

## Estado del Proyecto

🟢 **Fase 1 (MVP) - COMPLETADO** ✅
🟢 **Fase 2 (Impresora Virtual) - COMPLETADO** ✅
🟢 **Fase 3 (Servidor Completo) - COMPLETADO** ✅
🟢 **Fase 4 (Seguridad) - COMPLETADO** ✅
🟢 **Fase 5 (Interfaces de Usuario) - COMPLETADO** ✅

El sistema captura trabajos de impresión, los procesa con cola de prioridad, y los imprime en impresora física. Todo con comunicación TLS, autenticación JWT, API REST y dashboard web.

## Descripción

Printer_connect es un sistema que permite:

- **Cliente (Windows)**: Instala una impresora virtual que captura trabajos de impresión
- **Servidor**: Recibe archivos y parámetros de impresión (tamaño, márgenes, orientación)
- **Registro**: Guarda histórico de todas las impresiones realizadas
- **Simplicidad**: Evita problemas de configuración de impresoras en entornos Windows con dominio

### Ventajas

✅ **Centralizado**: Un solo servidor gestiona todas las impresiones
✅ **Simple**: No requiere configurar drivers en cada cliente
✅ **Auditable**: Registro completo de todas las impresiones
✅ **Flexible**: Parámetros configurables por trabajo

---

## Inicio Rápido

### Requisitos

- Python 3.10 o superior
- Windows (para el cliente con impresora virtual en fases futuras)
- Red local funcional

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Printer_connect
```

2. **Instalar dependencias del servidor**
```bash
cd server
pip install -r requirements.txt
cp config.ini.example config.ini
# Editar config.ini según tus necesidades
```

3. **Instalar dependencias del cliente**
```bash
cd ../client
pip install -r requirements.txt
cp config.ini.example config.ini
# Configurar la IP del servidor en config.ini
```

### Uso

#### Iniciar el Servidor

```bash
cd server
python main.py
```

#### Iniciar el Cliente

```bash
cd client
python main.py
```

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/ -v

# Test end-to-end de la Fase 1
python scripts/test_phase1.py
```

---

## Documentación

- 📖 [**Análisis Completo y Sugerencias**](ANALISIS_Y_SUGERENCIAS.md) - Análisis exhaustivo del proyecto
- 🚀 [**Guía de Inicio Rápido**](QUICKSTART.md) - Para desarrolladores
- 🗺️ [**Roadmap**](docs/ROADMAP.md) - Plan de desarrollo completo
- ✅ [**Fase 1 - MVP**](docs/FASE1_MVP.md) - Comunicación cliente-servidor
- ✅ [**Fase 2 - Impresora Virtual**](docs/FASE2_IMPRESORA_VIRTUAL.md) - Captura de impresiones
- ✅ [**Fase 3 - Servidor Completo**](docs/FASE3_SERVIDOR_COMPLETO.md) - Cola de impresión y base de datos
- ✅ [**Fase 4 - Seguridad**](docs/FASE4_SEGURIDAD.md) - TLS y autenticación
- ✅ [**Fase 5 - Interfaces de Usuario**](docs/FASE5_INTERFACES.md) - API REST y dashboard web (ACTUAL)
- 🔬 [**Investigación Impresora Virtual**](docs/INVESTIGACION_IMPRESORA_VIRTUAL.md) - Análisis técnico

---

## Arquitectura

### Fase 1 (Actual): Comunicación Básica

```
┌──────────────┐                    ┌──────────────┐
│   Cliente    │────── JSON/TCP ────>│   Servidor   │
│              │<─── Respuesta ──────│              │
└──────────────┘                    └──────────────┘
                                           │
                                           ▼
                                    [Archivos guardados
                                     en carpeta temp]
```

### Fases Futuras

- **Fase 2**: Impresora virtual en Windows
- **Fase 3**: Cola de impresión + impresora física
- **Fase 4**: Seguridad (TLS/SSL, autenticación)
- **Fase 5**: Interfaces de usuario
- **Fase 6**: Testing completo
- **Fase 7**: Deployment

Ver [ROADMAP.md](docs/ROADMAP.md) para detalles.

---

## Estructura del Proyecto

```
Printer_connect/
├── client/              # Cliente de impresión
├── server/              # Servidor de impresión
├── shared/              # Código compartido
├── docs/                # Documentación
├── tests/               # Tests
├── scripts/             # Scripts de utilidad
├── ANALISIS_Y_SUGERENCIAS.md
├── QUICKSTART.md
└── README.md
```

---

## Tecnologías

- **Lenguaje**: Python 3.10+
- **Comunicación**: TCP/IP con protocolo JSON
- **Configuración**: Archivos INI
- **Logging**: Módulo logging con rotación
- **Tests**: pytest

### Próximamente

- **Windows API**: pywin32 (impresora virtual)
- **Base de datos**: SQLite/PostgreSQL
- **Web**: FastAPI (interfaz de administración)
- **Seguridad**: cryptography, python-jose

---

## Características Implementadas

### Fase 1 - MVP
✅ Servidor TCP/IP multi-threaded
✅ Cliente TCP/IP con envío de archivos
✅ Protocolo de comunicación JSON
✅ Sistema de logging robusto
✅ Gestión de configuración
✅ Modelos de datos completos
✅ Tests unitarios
✅ Manejo de errores

### Fase 2 - Impresora Virtual
✅ Captura de trabajos de impresión en Windows
✅ Conversión PostScript → PDF (GhostScript)
✅ Extracción automática de parámetros
✅ Monitoreo de carpeta (watchdog)
✅ Envío automático al servidor
✅ Script de instalación PowerShell
✅ Mock converter para testing sin GhostScript

### Fase 3 - Servidor Completo
✅ Base de datos con SQLAlchemy (SQLite/PostgreSQL)
✅ Cola de impresión con prioridades
✅ Procesador de trabajos con reintentos
✅ Gestor de impresora multi-plataforma
✅ Soporte Windows (win32print)
✅ Soporte Linux (CUPS)
✅ Registro completo de trabajos
✅ Estadísticas y monitoreo

### Fase 4 - Seguridad
✅ Encriptación TLS/SSL (TLS 1.2+)
✅ Autenticación JWT con tokens
✅ Validación exhaustiva de inputs
✅ Rate limiting por cliente
✅ Hash de contraseñas (PBKDF2-SHA256)
✅ Generación de certificados
✅ Logs de auditoría
✅ Protección contra path traversal

### Fase 5 - Interfaces de Usuario
✅ API REST completa con FastAPI
✅ Sistema de gestión de usuarios (admin/user/viewer)
✅ Dashboard web responsive
✅ Login con autenticación JWT
✅ Estadísticas en tiempo real
✅ Lista y monitoreo de trabajos
✅ Documentación interactiva (Swagger/ReDoc)
✅ Auto-refresh de datos

---

## Próximos Pasos

1. **Fase 6**: Testing y Optimización
   - Tests unitarios completos
   - Tests de integración
   - Tests de carga
   - Optimización de rendimiento

2. **Fase 7**: Deployment
   - Instaladores completos
   - Servicios de Windows/Linux
   - Monitoreo con Prometheus/Grafana
   - Scripts de deployment

---

## Contribuir

Lee la [Guía de Inicio Rápido](QUICKSTART.md) para configurar el entorno de desarrollo.

### Flujo de Trabajo

1. Fork del proyecto
2. Crea una rama para tu feature
3. Implementa cambios con tests
4. Asegúrate de que todos los tests pasen
5. Commit con mensajes descriptivos
6. Push y crea Pull Request

---

## Licencia

[Especificar licencia]

---

## Contacto

[Información de contacto]

---

**Versión Actual**: 0.5.0
**Estado**: Fase 5 Completada ✅
**Características**: Sistema completo con TLS, JWT, API REST, dashboard web, gestión de usuarios, y monitoreo en tiempo real
