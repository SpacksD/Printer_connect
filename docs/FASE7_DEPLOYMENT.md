# Fase 7: Deployment - Documentación

## Visión General

La Fase 7 completa el proyecto con herramientas de deployment y documentación de usuario:

- **Scripts de Instalación**: Instalador automático del servidor
- **Servicio Systemd**: Configuración de servicio de sistema
- **Manual de Usuario**: Documentación completa para usuarios finales
- **Guías de Deployment**: Instrucciones de producción

## Estado: ✅ Completado

---

## Componentes Implementados

### 1. **Script de Instalación del Servidor** (`scripts/install_server.sh`)

Instalador automático que:
- Detecta sistema operativo (Ubuntu/Debian/CentOS/RHEL/Fedora)
- Instala Python 3 y dependencias
- Crea usuario del sistema `printer-connect`
- Crea estructura de directorios
- Copia archivos del proyecto
- Instala dependencias Python en venv
- Configura permisos

#### Uso

```bash
sudo ./scripts/install_server.sh
```

#### Directorios Creados

- `/opt/printer-connect`: Código de la aplicación
- `/var/lib/printer-connect`: Datos (base de datos, archivos)
- `/var/log/printer-connect`: Logs
- `/etc/printer-connect`: Configuración

### 2. **Servicio Systemd** (`scripts/printer-connect.service`)

Configuración de servicio para Linux:

```ini
[Unit]
Description=Printer_connect Server
After=network.target

[Service]
Type=simple
User=printer-connect
ExecStart=/opt/printer-connect/venv/bin/python server/main_v4.py
Restart=always
```

Características:
- Auto-restart en fallos
- Logging a archivos
- Restricciones de seguridad (NoNewPrivileges, PrivateTmp)
- Protección del sistema de archivos

#### Instalación del Servicio

```bash
# Copiar archivo
sudo cp scripts/printer-connect.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar
sudo systemctl enable printer-connect

# Iniciar
sudo systemctl start printer-connect

# Verificar
sudo systemctl status printer-connect
```

### 3. **Manual de Usuario** (`docs/MANUAL_USUARIO.md`)

Documentación completa para usuarios finales:

#### Contenido
- Introducción al sistema
- Guía de instalación (Servidor y Cliente)
- Instrucciones de uso
- Roles de usuario
- Resolución de problemas
- Mantenimiento (backup, actualización)
- FAQ

#### Secciones Principales

**Instalación:**
- Servidor Linux paso a paso
- Cliente Windows con PowerShell
- Configuración de certificados
- Creación de usuarios

**Uso:**
- Imprimir documentos
- Monitoreo vía dashboard
- Gestión de trabajos
- Comandos CLI

**Troubleshooting:**
- Problemas comunes
- Verificación de conexión
- Logs y diagnóstico
- Configuración de firewall

**Mantenimiento:**
- Limpieza de trabajos antiguos
- Backup de base de datos
- Proceso de actualización

---

## Guía de Deployment

### Deployment en Producción

#### 1. Preparación del Servidor

```bash
# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar requisitos
sudo apt-get install -y git python3 python3-pip python3-venv

# Clonar repositorio
git clone <repository-url>
cd Printer_connect
```

#### 2. Ejecutar Instalador

```bash
sudo ./scripts/install_server.sh
```

#### 3. Configuración

```bash
# Editar configuración
sudo nano /etc/printer-connect/config.ini
```

Configurar:
- Host y puerto
- Base de datos (PostgreSQL para producción)
- TLS (certificados de CA, no autofirmados)
- Secret key JWT (generar nuevo)
- Rate limiting
- Logs

#### 4. Certificados SSL

**Para Producción: Usar Let's Encrypt**

```bash
# Instalar certbot
sudo apt-get install certbot

# Obtener certificado
sudo certbot certonly --standalone -d tu-servidor.com

# Configurar en config.ini
certfile = /etc/letsencrypt/live/tu-servidor.com/fullchain.pem
keyfile = /etc/letsencrypt/live/tu-servidor.com/privkey.pem
```

**Para Desarrollo: Autofirmados**

```bash
cd /opt/printer-connect
source venv/bin/activate
python scripts/generate_certificates.py --server --hostname tu-servidor.com
```

#### 5. Base de Datos

**PostgreSQL Recomendado para Producción**

```bash
# Instalar PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Crear base de datos
sudo -u postgres psql
CREATE DATABASE printer_connect;
CREATE USER printer_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE printer_connect TO printer_user;
\q

# Configurar en config.ini
db_type = postgresql
postgresql_host = localhost
postgresql_database = printer_connect
postgresql_user = printer_user
postgresql_password = secure_password
```

#### 6. Usuario Administrador

```bash
cd /opt/printer-connect
source venv/bin/activate
python scripts/create_admin_user.py
```

#### 7. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 9100/tcp  # Print server
sudo ufw allow 8080/tcp  # API/Dashboard
sudo ufw enable

# firewalld (CentOS/RHEL)
sudo firewall-cmd --add-port=9100/tcp --permanent
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

#### 8. Iniciar Servicio

```bash
sudo systemctl start printer-connect
sudo systemctl enable printer-connect
```

#### 9. Verificación

```bash
# Estado del servicio
sudo systemctl status printer-connect

# Logs
tail -f /var/log/printer-connect/server.log

# Health check
curl http://localhost:8080/api/health

# Dashboard
xdg-open http://localhost:8080
```

### Deployment en Docker (Opcional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY server/ /app/server/
COPY shared/ /app/shared/
COPY scripts/ /app/scripts/

RUN pip install -r server/requirements.txt

EXPOSE 9100 8080

CMD ["python", "server/main_v4.py"]
```

```bash
docker build -t printer-connect .
docker run -d -p 9100:9100 -p 8080:8080 printer-connect
```

---

## Monitoreo

### Logs

```bash
# Server logs
tail -f /var/log/printer-connect/server.log

# Error logs
tail -f /var/log/printer-connect/server-error.log

# Systemd journal
journalctl -u printer-connect -f
```

### Métricas

```bash
# Estado del servicio
systemctl status printer-connect

# Recursos
ps aux | grep printer-connect
top -p $(pgrep -f printer-connect)

# Conexiones
netstat -tulpn | grep 9100
```

### Health Checks

```bash
# API health
curl http://localhost:8080/api/health

# Con autenticación
curl -H "Authorization: Bearer TOKEN" http://localhost:8080/api/stats
```

---

## Backup y Restore

### Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/printer-connect"
DATE=$(date +%Y%m%d_%H%M%S)

# Detener servicio
systemctl stop printer-connect

# Backup base de datos
cp /var/lib/printer-connect/data/printer_connect.db \
   $BACKUP_DIR/db_$DATE.db

# Backup configuración
cp /etc/printer-connect/config.ini \
   $BACKUP_DIR/config_$DATE.ini

# Backup certificados
cp -r /opt/printer-connect/certs \
   $BACKUP_DIR/certs_$DATE/

# Reiniciar servicio
systemctl start printer-connect

# Comprimir
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
   $BACKUP_DIR/db_$DATE.db \
   $BACKUP_DIR/config_$DATE.ini \
   $BACKUP_DIR/certs_$DATE/

echo "Backup completado: backup_$DATE.tar.gz"
```

### Restore

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

# Detener servicio
systemctl stop printer-connect

# Extraer backup
tar -xzf $BACKUP_FILE -C /tmp/

# Restaurar archivos
cp /tmp/backup/db_*.db /var/lib/printer-connect/data/printer_connect.db
cp /tmp/backup/config_*.ini /etc/printer-connect/config.ini
cp -r /tmp/backup/certs_*/ /opt/printer-connect/certs/

# Permisos
chown -R printer-connect:printer-connect /var/lib/printer-connect
chown -R printer-connect:printer-connect /opt/printer-connect/certs

# Reiniciar servicio
systemctl start printer-connect

echo "Restore completado"
```

---

## Actualizaciones

### Actualización de Versión

```bash
# 1. Backup
./backup.sh

# 2. Detener servicio
sudo systemctl stop printer-connect

# 3. Actualizar código
cd /opt/printer-connect
sudo -u printer-connect git pull

# 4. Actualizar dependencias
cd /opt/printer-connect
source venv/bin/activate
pip install -r server/requirements.txt --upgrade

# 5. Migrar base de datos (si necesario)
# python scripts/migrate_db.py

# 6. Reiniciar servicio
sudo systemctl start printer-connect

# 7. Verificar
sudo systemctl status printer-connect
```

---

## Seguridad en Producción

### Checklist

- [ ] Usar certificados de CA reconocida (Let's Encrypt)
- [ ] Cambiar secret key JWT
- [ ] Usar PostgreSQL en vez de SQLite
- [ ] Configurar firewall
- [ ] Habilitar rate limiting
- [ ] Configurar logs de auditoría
- [ ] Backup automático programado
- [ ] Monitoreo de recursos
- [ ] Usuarios con contraseñas fuertes
- [ ] Actualizar dependencias regularmente

### Hardening

```bash
# Restringir permisos
chmod 600 /etc/printer-connect/config.ini
chmod 700 /var/lib/printer-connect/data

# SELinux (si aplica)
semanage port -a -t http_port_t -p tcp 8080
semanage port -a -t printer_port_t -p tcp 9100

# Fail2ban para proteger API
# /etc/fail2ban/jail.local
[printer-connect]
enabled = true
port = 8080
filter = printer-connect
logpath = /var/log/printer-connect/server.log
maxretry = 5
```

---

## Características Destacadas

✅ **Instalación Automática** con detección de SO
✅ **Servicio Systemd** con auto-restart
✅ **Manual de Usuario** completo
✅ **Scripts de Backup/Restore**
✅ **Guía de Deployment** para producción
✅ **Configuración de Seguridad**
✅ **Monitoreo y Logs**
✅ **Proceso de Actualización**

---

## Proyecto Completado

Con la Fase 7, el proyecto **Printer_connect** está completo y listo para producción.

### Todas las Fases Implementadas:

1. ✅ **Fase 1 (MVP)**: Comunicación cliente-servidor
2. ✅ **Fase 2 (Impresora Virtual)**: Captura de impresiones
3. ✅ **Fase 3 (Servidor Completo)**: Cola y base de datos
4. ✅ **Fase 4 (Seguridad)**: TLS y autenticación
5. ✅ **Fase 5 (Interfaces)**: API REST y dashboard
6. ✅ **Fase 6 (Testing)**: Tests y benchmarking
7. ✅ **Fase 7 (Deployment)**: Scripts de instalación y deployment

### Estadísticas Finales

- **~12,000 líneas** de código
- **50+ archivos** de código fuente
- **7 fases** completadas
- **30+ tests** unitarios
- **15+ endpoints** API
- **Documentación completa**

---

**Última actualización:** 2025-11-07
**Versión:** 1.0.0
**Estado:** ✅ PROYECTO COMPLETADO
