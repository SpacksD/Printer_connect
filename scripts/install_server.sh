#!/bin/bash
# Script de instalación del servidor Printer_connect

set -e

echo "========================================"
echo " Printer_connect - Instalación Servidor"
echo "========================================"
echo

# Verificar permisos
if [[ $EUID -ne 0 ]]; then
   echo "❌ Este script debe ejecutarse como root"
   echo "   Usa: sudo ./install_server.sh"
   exit 1
fi

# Detectar sistema operativo
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ No se pudo detectar el sistema operativo"
    exit 1
fi

echo "Sistema detectado: $OS"
echo

# 1. Instalar Python y dependencias
echo "[1/6] Instalando Python y dependencias del sistema..."
case $OS in
    ubuntu|debian)
        apt-get update
        apt-get install -y python3 python3-pip python3-venv
        ;;
    centos|rhel|fedora)
        yum install -y python3 python3-pip
        ;;
    *)
        echo "⚠️  Sistema no soportado: $OS"
        echo "   Instala Python 3.10+ manualmente"
        ;;
esac

# 2. Crear usuario del sistema
echo "[2/6] Creando usuario printer-connect..."
if ! id printer-connect &>/dev/null; then
    useradd -r -s /bin/false printer-connect
    echo "✓ Usuario creado"
else
    echo "✓ Usuario ya existe"
fi

# 3. Crear directorios
echo "[3/6] Creando directorios..."
mkdir -p /opt/printer-connect
mkdir -p /var/lib/printer-connect/data
mkdir -p /var/log/printer-connect
mkdir -p /etc/printer-connect

# 4. Copiar archivos
echo "[4/6] Copiando archivos..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -r "$SCRIPT_DIR/server" /opt/printer-connect/
cp -r "$SCRIPT_DIR/shared" /opt/printer-connect/
cp "$SCRIPT_DIR/server/config.ini.example" /etc/printer-connect/config.ini

# 5. Instalar dependencias Python
echo "[5/6] Instalando dependencias Python..."
cd /opt/printer-connect
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt

# 6. Configurar permisos
echo "[6/6] Configurando permisos..."
chown -R printer-connect:printer-connect /opt/printer-connect
chown -R printer-connect:printer-connect /var/lib/printer-connect
chown -R printer-connect:printer-connect /var/log/printer-connect
chown -R printer-connect:printer-connect /etc/printer-connect

echo
echo "========================================"
echo " Instalación Completada"
echo "========================================"
echo
echo "Próximos pasos:"
echo
echo "1. Editar configuración:"
echo "   nano /etc/printer-connect/config.ini"
echo
echo "2. Generar certificados SSL:"
echo "   cd /opt/printer-connect"
echo "   source venv/bin/activate"
echo "   python scripts/generate_certificates.py --server"
echo
echo "3. Crear usuario administrador:"
echo "   python scripts/create_admin_user.py"
echo
echo "4. Instalar servicio systemd:"
echo "   cp scripts/printer-connect.service /etc/systemd/system/"
echo "   systemctl enable printer-connect"
echo "   systemctl start printer-connect"
echo
echo "5. Verificar estado:"
echo "   systemctl status printer-connect"
echo
