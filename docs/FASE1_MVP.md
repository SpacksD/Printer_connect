# Fase 1 - MVP (Mínimo Producto Viable)

## Estado: ✅ COMPLETADO

---

## Objetivos

✅ Comunicación básica cliente-servidor funcionando
✅ Cliente envía archivos PDF al servidor
✅ Servidor recibe y guarda archivos
✅ Logging implementado
✅ Tests básicos creados

---

## Componentes Implementados

### 1. Infraestructura Base

#### Sistema de Logging
- **Cliente**: `client/utils/logger.py`
- **Servidor**: `server/utils/logger.py`
- Rotación de archivos automática
- Niveles configurables (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Salida a consola y archivo

#### Gestor de Configuración
- **Cliente**: `client/utils/config.py`
- **Servidor**: `server/utils/config.py`
- Archivos INI para configuración
- Valores por defecto
- Generación automática de client_id

### 2. Protocolo de Comunicación

#### Protocolo Compartido
- **Archivo**: `shared/protocol.py`
- Mensajes JSON sobre TCP/IP
- Header de 4 bytes con longitud del mensaje
- Soporte para Unicode
- Serialización/Deserialización automática

#### Funciones Helper
- `create_print_job_message()`: Crea mensaje de trabajo de impresión
- `create_response_message()`: Crea mensaje de respuesta
- Codificación Base64 para archivos binarios

### 3. Servidor

#### PrintServer (`server/network/server.py`)
Características:
- Escucha en puerto configurable (por defecto 9100)
- Manejo de múltiples clientes simultáneos (threading)
- Recepción de trabajos de impresión
- Guardado de archivos en carpeta temporal
- Respuestas estructuradas
- Manejo robusto de errores

#### Punto de Entrada (`server/main.py`)
- Carga de configuración
- Inicialización de logging
- Manejo de señales (SIGINT, SIGTERM)
- Cierre limpio del servidor

### 4. Cliente

#### PrintClient (`client/network/client.py`)
Características:
- Conexión al servidor
- Envío de trabajos de impresión
- Test de conectividad
- Timeout configurable
- Manejo de errores de red

#### Punto de Entrada (`client/main.py`)
- Carga de configuración
- Inicialización de logging
- Test de conexión automático
- Creación de PDF de prueba
- Envío de trabajo de ejemplo

### 5. Modelos de Datos

#### Compartidos (`shared/data_models.py`)
- `PrintMargins`: Márgenes de impresión
- `PrintParameters`: Parámetros de impresión (tamaño, orientación, etc.)
- `PrintJobMetadata`: Metadatos del documento
- `PrintJob`: Trabajo de impresión completo
- `ServerResponse`: Respuesta del servidor

Todos con:
- Serialización/Deserialización a/desde diccionarios
- Valores por defecto sensatos
- Type hints completos

### 6. Tests

#### Tests del Protocolo (`tests/test_protocol.py`)
- Creación de mensajes
- Serialización/Deserialización JSON
- Codificación/Decodificación binaria
- Soporte Unicode
- Funciones helper

#### Tests de Modelos (`tests/test_data_models.py`)
- PrintMargins
- PrintParameters
- PrintJobMetadata
- Conversiones to_dict/from_dict

#### Test End-to-End (`scripts/test_phase1.py`)
- Servidor y cliente en el mismo proceso
- Prueba completa de comunicación
- Verificación de éxito

---

## Arquitectura Implementada

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTE                              │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  main.py     │────────>│ PrintClient  │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │   Protocol      │               │
│                          └────────┬────────┘               │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │   TCP Socket    │               │
│                          └────────┬────────┘               │
└───────────────────────────────────┼─────────────────────────┘
                                    │
                                    │ JSON/TCP
                                    │
┌───────────────────────────────────▼─────────────────────────┐
│                        SERVIDOR                             │
│                                                             │
│                          ┌────────────────┐                │
│                          │   TCP Socket   │                │
│                          └────────┬───────┘                │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │   Protocol      │               │
│                          └────────┬────────┘               │
│                                   │                         │
│  ┌──────────────┐         ┌──────▼───────┐                │
│  │  main.py     │<────────│ PrintServer  │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │  Save to File   │               │
│                          │  (temp folder)  │               │
│                          └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## Formato de Mensajes

### Mensaje de Trabajo de Impresión
```json
{
  "version": "1.0",
  "message_type": "print_job",
  "timestamp": "2025-11-07T12:34:56",
  "data": {
    "client_id": "abc-123-def",
    "user": "usuario",
    "file_content": "<base64_encoded_file>",
    "file_format": "pdf",
    "parameters": {
      "page_size": "A4",
      "orientation": "portrait",
      "margins": {"top": 10, "bottom": 10, "left": 10, "right": 10},
      "copies": 1,
      "color": true,
      "duplex": false,
      "quality": "normal"
    },
    "metadata": {
      "document_name": "documento.pdf",
      "page_count": 1,
      "application": "Test App",
      "file_size_bytes": 1024
    }
  }
}
```

### Respuesta del Servidor
```json
{
  "version": "1.0",
  "message_type": "response",
  "timestamp": "2025-11-07T12:34:57",
  "data": {
    "status": "success",
    "message": "Trabajo de impresión recibido y procesado",
    "job_id": "JOB-20251107-abc12345",
    "queue_position": 1,
    "error_code": null
  }
}
```

---

## Uso

### Iniciar el Servidor

```bash
cd server
python main.py
```

Salida esperada:
```
============================================================
 Printer_connect - Servidor
 Versión 0.1.0 (MVP)
============================================================

Cargando configuración desde: config.ini

Servidor iniciando en 0.0.0.0:9100
Carpeta temporal: ./temp
Log: ./logs/server.log

Presiona Ctrl+C para detener el servidor
------------------------------------------------------------

Servidor escuchando en 0.0.0.0:9100
```

### Iniciar el Cliente

```bash
cd client
python main.py
```

Salida esperada:
```
============================================================
 Printer_connect - Cliente
 Versión 0.1.0 (MVP)
============================================================

Cargando configuración desde: config.ini

Servidor configurado: 127.0.0.1:9100
Client ID: abc-123-def-456
Usuario: tu_usuario

Probando conexión con el servidor...
✓ Conexión exitosa

------------------------------------------------------------
Enviando trabajo de impresión de prueba...
Archivo: test_print.pdf
Tamaño: 190 bytes

============================================================
 RESPUESTA DEL SERVIDOR
============================================================
Estado: SUCCESS
Mensaje: Trabajo de impresión recibido y procesado: JOB-20251107-abc12345
Job ID: JOB-20251107-abc12345
Posición en cola: 1
============================================================

✓ Trabajo de impresión enviado exitosamente
```

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/ -v

# Test end-to-end
python scripts/test_phase1.py
```

---

## Estructura de Archivos

```
Printer_connect/
│
├── client/
│   ├── __init__.py
│   ├── main.py                    # Punto de entrada del cliente
│   ├── config.ini.example         # Configuración de ejemplo
│   ├── network/
│   │   ├── __init__.py
│   │   ├── client.py             # Cliente TCP/IP
│   │   └── protocol.py           # Protocolo del cliente
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Sistema de logging
│       └── config.py             # Gestor de configuración
│
├── server/
│   ├── __init__.py
│   ├── main.py                    # Punto de entrada del servidor
│   ├── config.ini.example         # Configuración de ejemplo
│   ├── network/
│   │   ├── __init__.py
│   │   ├── server.py             # Servidor TCP/IP
│   │   └── protocol.py           # Protocolo del servidor
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Sistema de logging
│       └── config.py             # Gestor de configuración
│
├── shared/
│   ├── __init__.py
│   ├── constants.py              # Constantes
│   ├── data_models.py            # Modelos de datos
│   ├── exceptions.py             # Excepciones
│   └── protocol.py               # Protocolo de comunicación
│
├── tests/
│   ├── __init__.py
│   ├── test_protocol.py          # Tests del protocolo
│   └── test_data_models.py       # Tests de modelos
│
└── scripts/
    └── test_phase1.py            # Test end-to-end
```

---

## Métricas de Éxito

### Funcionalidad
- ✅ 100% de mensajes llegan al servidor
- ✅ Archivos se guardan correctamente
- ✅ Respuestas se reciben en el cliente

### Calidad del Código
- ✅ Type hints en todos los métodos
- ✅ Docstrings en todas las funciones
- ✅ Manejo de errores robusto
- ✅ Tests unitarios implementados

### Logging
- ✅ Todos los eventos importantes se registran
- ✅ Niveles de log apropiados
- ✅ Rotación de archivos de log

---

## Próximos Pasos (Fase 2)

La Fase 1 sienta las bases para:

1. **Impresora Virtual** (Fase 2)
   - Captura de trabajos de impresión en Windows
   - Integración con GhostScript
   - Conversión automática a PDF

2. **Servidor Completo** (Fase 3)
   - Cola de impresión
   - Interfaz con impresora física
   - Base de datos

3. **Seguridad** (Fase 4)
   - Autenticación JWT
   - Encriptación TLS/SSL

---

## Notas Técnicas

### Protocolo de Red
- **Formato**: Length-prefixed JSON
- **Header**: 4 bytes (unsigned int, big-endian)
- **Encoding**: UTF-8
- **Puerto por defecto**: 9100 (AppSocket/JetDirect)

### Manejo de Errores
- Excepciones específicas en `shared/exceptions.py`
- Respuestas de error estructuradas
- Logging detallado de errores
- Cierre limpio de conexiones

### Threading
- Servidor multi-threaded
- Un thread por cliente
- Daemon threads para limpieza automática

### Configuración
- Archivos INI para fácil edición
- Valores por defecto sensatos
- Generación automática si no existe

---

## Conclusión

La **Fase 1 (MVP)** está **completa y funcionando**. El sistema puede:

✅ Establecer conexión TCP/IP entre cliente y servidor
✅ Enviar archivos PDF desde el cliente
✅ Recibir y guardar archivos en el servidor
✅ Responder con confirmación estructurada
✅ Manejar errores de manera robusta
✅ Registrar toda la actividad en logs

**Todo está listo para avanzar a la Fase 2: Impresora Virtual**

---

**Creado**: 2025-11-07
**Estado**: Completado
**Versión**: 0.1.0
