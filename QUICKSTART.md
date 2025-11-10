# Guía de Inicio Rápido - Printer_connect

## 🚀 Inicio Rápido para Desarrollo

### Prerrequisitos

- Python 3.10 o superior
- Git
- Windows (para desarrollo del cliente con impresora virtual)
- (Opcional) GhostScript para impresora virtual

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd Printer_connect
```

### 2. Configurar Servidor

```bash
# Navegar al directorio del servidor
cd server

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración de ejemplo
cp config.ini.example config.ini

# Editar config.ini según tus necesidades
# notepad config.ini  (Windows)
# nano config.ini     (Linux)
```

### 3. Configurar Cliente

```bash
# Abrir otra terminal y navegar al directorio del cliente
cd client

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración de ejemplo
cp config.ini.example config.ini

# Editar config.ini - IMPORTANTE: configurar IP del servidor
# notepad config.ini  (Windows)
```

### 4. Inicializar Base de Datos (Servidor)

```bash
cd server

# Ejecutar script de inicialización (cuando esté disponible)
python scripts/setup_database.py
```

### 5. Ejecutar en Modo Desarrollo

**Terminal 1 - Servidor:**
```bash
cd server
venv\Scripts\activate
python main.py
```

**Terminal 2 - Cliente:**
```bash
cd client
venv\Scripts\activate
python main.py
```

---

## 📋 Próximos Pasos

Una vez que el entorno esté configurado:

### Para Desarrolladores:

1. **Revisar la arquitectura**: Lee `ANALISIS_Y_SUGERENCIAS.md` completo
2. **Entender el roadmap**: Lee `docs/ROADMAP.md`
3. **Explorar el código compartido**: Revisa `shared/data_models.py` y `shared/constants.py`
4. **Empezar por el MVP**: Comienza implementando la Fase 1 del roadmap

### Tareas Inmediatas:

#### Servidor (Fase 1 - MVP):
```python
# server/main.py - Esqueleto básico

import socket
import json
from shared.constants import DEFAULT_PORT

def start_server():
    """Servidor TCP/IP básico"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', DEFAULT_PORT))
    server_socket.listen(5)

    print(f"Servidor escuchando en puerto {DEFAULT_PORT}...")

    while True:
        client_socket, address = server_socket.accept()
        print(f"Conexión desde {address}")

        # TODO: Implementar recepción de archivo
        # TODO: Implementar guardado en carpeta temporal
        # TODO: Implementar logging

        client_socket.close()

if __name__ == "__main__":
    start_server()
```

#### Cliente (Fase 1 - MVP):
```python
# client/main.py - Esqueleto básico

import socket
import json
from pathlib import Path
from shared.constants import DEFAULT_PORT

def send_file(server_ip: str, file_path: Path):
    """Envía un archivo al servidor"""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((server_ip, DEFAULT_PORT))
        print(f"Conectado a {server_ip}:{DEFAULT_PORT}")

        # TODO: Implementar lectura de archivo
        # TODO: Implementar serialización
        # TODO: Implementar envío
        # TODO: Implementar recepción de respuesta

        print("Archivo enviado exitosamente")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        client_socket.close()

if __name__ == "__main__":
    # Test: enviar un PDF de prueba
    server_ip = "192.168.1.100"  # Cambiar por tu IP
    test_file = Path("test.pdf")
    send_file(server_ip, test_file)
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# En el directorio raíz
pytest tests/

# Con cobertura
pytest --cov=. --cov-report=html tests/

# Tests específicos
pytest tests/client/
pytest tests/server/
```

---

## 🔧 Herramientas Útiles

### Verificar Comunicación de Red

```bash
# Verificar que el puerto esté abierto
netstat -an | grep 9100

# Probar conectividad
telnet localhost 9100

# En Windows PowerShell:
Test-NetConnection -ComputerName localhost -Port 9100
```

### Monitorear Logs en Tiempo Real

```bash
# Linux/Mac
tail -f /var/log/printer_connect/server.log

# Windows PowerShell
Get-Content server.log -Wait
```

---

## 📚 Estructura del Proyecto

```
Printer_connect/
│
├── client/              # Código del cliente
├── server/              # Código del servidor
├── shared/              # Código compartido
│   ├── constants.py     # Constantes
│   ├── data_models.py   # Modelos de datos
│   └── exceptions.py    # Excepciones
├── docs/                # Documentación
│   └── ROADMAP.md
├── tests/               # Tests
├── scripts/             # Scripts de utilidad
│
├── README.md
├── ANALISIS_Y_SUGERENCIAS.md  # ⭐ Lee esto primero
├── QUICKSTART.md        # Este archivo
└── .gitignore
```

---

## ❓ FAQ

### ¿Por qué usar el puerto 9100?
Es el puerto estándar para impresoras de red (AppSocket/HP JetDirect). Facilita la integración y evita conflictos con otros servicios comunes.

### ¿Necesito GhostScript desde el principio?
No. Para el MVP (Fase 1), puedes trabajar solo con archivos PDF. GhostScript es necesario para la Fase 2 cuando implementes la impresora virtual.

### ¿Funciona en Linux?
El servidor sí. El cliente está diseñado para Windows porque utiliza APIs específicas de Windows para la impresora virtual. Se podría adaptar para Linux usando CUPS.

### ¿Cómo depuro problemas de red?
1. Verifica que el servidor esté corriendo: `netstat -an | grep 9100`
2. Verifica conectividad: `telnet <server-ip> 9100`
3. Revisa logs del servidor
4. Usa Wireshark para ver tráfico si es necesario

---

## 🆘 Troubleshooting

### Error: "Address already in use"
```bash
# Encuentra el proceso usando el puerto
netstat -ano | findstr :9100  # Windows
lsof -i :9100                  # Linux/Mac

# Mata el proceso o cambia el puerto en config.ini
```

### Error: "Connection refused"
- Verifica que el servidor esté corriendo
- Verifica firewall (debe permitir conexiones en el puerto 9100)
- Verifica que la IP en config.ini del cliente sea correcta

### Error al instalar pywin32
```bash
# En Windows, puede requerir permisos de administrador
pip install --user pywin32

# O usar conda
conda install pywin32
```

---

## 📖 Recursos Adicionales

- **Análisis completo**: `ANALISIS_Y_SUGERENCIAS.md`
- **Roadmap**: `docs/ROADMAP.md`
- **Modelos de datos**: `shared/data_models.py`
- **Constantes**: `shared/constants.py`

---

## 🤝 Contribuir

1. Lee `ANALISIS_Y_SUGERENCIAS.md` completo
2. Revisa el roadmap en `docs/ROADMAP.md`
3. Crea una rama para tu feature: `git checkout -b feature/nombre-feature`
4. Escribe tests para tu código
5. Asegúrate de que todos los tests pasen: `pytest`
6. Commit con mensajes descriptivos
7. Push y crea un Pull Request

---

## 📞 Contacto y Soporte

- **Issues**: Reporta bugs y solicita features en GitHub Issues
- **Documentación**: Consulta `docs/` para documentación detallada

---

**¡Listo para empezar! 🚀**

Empieza revisando `ANALISIS_Y_SUGERENCIAS.md` y luego implementa la Fase 1 del `docs/ROADMAP.md`.
