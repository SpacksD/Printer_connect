# Manual de Usuario - Printer_connect

## Introducción

Printer_connect es un sistema cliente-servidor que simplifica la impresión en red al eliminar la necesidad de configurar drivers de impresora en cada computadora.

## Componentes del Sistema

### Servidor
- Recibe trabajos de impresión de los clientes
- Gestiona cola de impresión con prioridades
- Imprime en impresora física
- Provee dashboard web para monitoreo

### Cliente
- Impresora virtual en Windows
- Captura trabajos de impresión
- Envía automáticamente al servidor

## Instalación

### Servidor (Linux)

1. **Ejecutar instalador:**
```bash
sudo ./scripts/install_server.sh
```

2. **Configurar:**
```bash
sudo nano /etc/printer-connect/config.ini
```

3. **Generar certificados:**
```bash
cd /opt/printer-connect
source venv/bin/activate
python scripts/generate_certificates.py --server
```

4. **Crear administrador:**
```bash
python scripts/create_admin_user.py
```

5. **Iniciar servicio:**
```bash
sudo systemctl start printer-connect
sudo systemctl enable printer-connect
```

### Cliente (Windows)

1. **Instalar prerrequisitos:**
   - Python 3.10+
   - GhostScript

2. **Ejecutar instalador:**
```powershell
.\scripts\install_printer_windows.ps1
```

3. **Configurar cliente:**
   - Editar `client/config.ini`
   - Configurar dirección del servidor
   - Copiar certificado del servidor

## Uso

### Imprimir un Documento

1. Abrir documento en cualquier aplicación
2. Archivo → Imprimir
3. Seleccionar "Printer_connect"
4. Ajustar configuración (copias, color, etc.)
5. Imprimir

El documento se enviará automáticamente al servidor y se añadirá a la cola de impresión.

### Monitorear Trabajos

#### Dashboard Web

1. Abrir navegador en `http://servidor:8080`
2. Iniciar sesión con credenciales
3. Ver estadísticas y trabajos en tiempo real

#### Línea de Comandos

```bash
# Ver estado del servicio
systemctl status printer-connect

# Ver logs
tail -f /var/log/printer-connect/server.log

# Ver cola de impresión
# (Requiere acceso a la API)
curl -H "Authorization: Bearer TOKEN" http://servidor:8080/api/jobs
```

## Roles de Usuario

### Admin
- Acceso completo al sistema
- Gestión de usuarios
- Ver todos los trabajos
- Configuración del servidor

### User
- Enviar trabajos de impresión
- Ver sus propios trabajos
- Ver estadísticas generales

### Viewer
- Solo lectura
- Ver trabajos y estadísticas
- No puede enviar trabajos

## Resolución de Problemas

### El trabajo no se imprime

1. **Verificar conexión:**
```bash
ping servidor
```

2. **Verificar servicio:**
```bash
systemctl status printer-connect
```

3. **Verificar logs:**
```bash
tail -f /var/log/printer-connect/server.log
```

4. **Verificar impresora:**
   - Impresora encendida
   - Papel disponible
   - Sin atascos

### Error de conexión

1. **Verificar certificados:**
   - Cliente tiene certificado del servidor
   - Certificados no expirados

2. **Verificar firewall:**
```bash
# Abrir puerto 9100 (impresión) y 8080 (web)
sudo firewall-cmd --add-port=9100/tcp --permanent
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

3. **Verificar configuración:**
   - Dirección del servidor correcta en cliente
   - Puerto correcto (9100 por defecto)

### Impresora virtual no aparece (Windows)

1. **Verificar instalación:**
   - GhostScript instalado
   - RedMon instalado
   - Script de proceso configurado

2. **Reinstalar impresora:**
```powershell
.\scripts\install_printer_windows.ps1
```

## Mantenimiento

### Limpieza de trabajos antiguos

Los trabajos completados se retienen por 30 días (configurable). Para limpiar manualmente:

```python
from server.database.database import DatabaseManager
db = DatabaseManager()
deleted = db.cleanup_old_jobs(days=30)
print(f"Eliminados {deleted} trabajos")
```

### Backup de base de datos

```bash
# Detener servicio
sudo systemctl stop printer-connect

# Copiar base de datos
sudo cp /var/lib/printer-connect/data/printer_connect.db /backup/

# Reiniciar servicio
sudo systemctl start printer-connect
```

### Actualización

1. **Backup:**
```bash
sudo systemctl stop printer-connect
sudo cp -r /opt/printer-connect /backup/
```

2. **Actualizar código:**
```bash
cd /opt/printer-connect
git pull
```

3. **Actualizar dependencias:**
```bash
source venv/bin/activate
pip install -r server/requirements.txt --upgrade
```

4. **Reiniciar:**
```bash
sudo systemctl start printer-connect
```

## Soporte

### Logs

- **Servidor:** `/var/log/printer-connect/server.log`
- **Errores:** `/var/log/printer-connect/server-error.log`
- **Cliente:** `C:\ProgramData\Printer_connect\client.log`

### Información del Sistema

```bash
# Versión
cat /opt/printer-connect/VERSION

# Estado
systemctl status printer-connect

# Recursos
top -p $(pgrep -f printer-connect)
```

### Reportar Problemas

Incluir en el reporte:
- Versión del sistema
- Sistema operativo
- Logs relevantes
- Pasos para reproducir

## FAQ

**Q: ¿Funciona en macOS/Linux como cliente?**
A: Actualmente solo Windows. Soporte para otros OS en desarrollo.

**Q: ¿Cuántos clientes soporta?**
A: Hasta 50 clientes simultáneos en hardware moderado.

**Q: ¿Puedo usar varias impresoras físicas?**
A: Actualmente una impresora por servidor. Multi-printer en desarrollo.

**Q: ¿Los documentos se guardan?**
A: Sí, en el servidor por 30 días (configurable).

**Q: ¿Es seguro?**
A: Sí. Usa TLS 1.2+ y JWT. Recomendamos certificados CA para producción.

---

**Última actualización:** 2025-11-07
**Versión:** 1.0.0
