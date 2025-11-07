# Script de instalación de impresora virtual Printer_connect
# Requiere permisos de administrador
# Requiere GhostScript y RedMon instalados previamente

#Requires -RunAsAdministrator

param(
    [string]$PrinterName = "Printer_connect",
    [string]$PortName = "RPT1:",
    [string]$DriverName = "MS Publisher Color Printer",
    [string]$PythonScript = ""
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Instalador de Impresora Virtual - Printer_connect" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Función para verificar si un comando existe
function Test-Command {
    param($CommandName)
    return [bool](Get-Command -Name $CommandName -ErrorAction SilentlyContinue)
}

# Verificar permisos de administrador
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Este script requiere permisos de administrador" -ForegroundColor Red
    Write-Host "Por favor, ejecuta PowerShell como administrador" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/6] Verificando requisitos..." -ForegroundColor Yellow

# Verificar Python
if (-not (Test-Command python)) {
    Write-Host "  ERROR: Python no está instalado o no está en el PATH" -ForegroundColor Red
    Write-Host "  Instala Python 3.10+ desde https://www.python.org" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = python --version
Write-Host "  ✓ Python encontrado: $pythonVersion" -ForegroundColor Green

# Verificar GhostScript
$gsPaths = @(
    "C:\Program Files\gs\gs10.02.0\bin\gswin64c.exe",
    "C:\Program Files\gs\gs10.01.0\bin\gswin64c.exe",
    "C:\Program Files\gs\gs9.56.1\bin\gswin64c.exe",
    "C:\Program Files (x86)\gs\gs10.02.0\bin\gswin32c.exe"
)

$gsFound = $false
foreach ($path in $gsPaths) {
    if (Test-Path $path) {
        Write-Host "  ✓ GhostScript encontrado: $path" -ForegroundColor Green
        $gsFound = $true
        break
    }
}

if (-not $gsFound) {
    Write-Host "  ERROR: GhostScript no encontrado" -ForegroundColor Red
    Write-Host "  Instala GhostScript desde https://www.ghostscript.com/download/" -ForegroundColor Yellow
    exit 1
}

# Verificar RedMon
$redmonPath = "$env:SystemRoot\System32\redmon39.dll"
if (-not (Test-Path $redmonPath)) {
    Write-Host "  ERROR: RedMon no está instalado" -ForegroundColor Red
    Write-Host "  Instala RedMon desde http://pages.cs.wisc.edu/~ghost/redmon/" -ForegroundColor Yellow
    exit 1
}

Write-Host "  ✓ RedMon encontrado" -ForegroundColor Green

Write-Host ""
Write-Host "[2/6] Verificando si la impresora ya existe..." -ForegroundColor Yellow

$existingPrinter = Get-Printer -Name $PrinterName -ErrorAction SilentlyContinue

if ($existingPrinter) {
    Write-Host "  La impresora '$PrinterName' ya existe" -ForegroundColor Yellow
    $response = Read-Host "  ¿Deseas eliminarla y reinstalarla? (S/N)"

    if ($response -eq 'S' -or $response -eq 's') {
        Write-Host "  Eliminando impresora existente..." -ForegroundColor Yellow
        Remove-Printer -Name $PrinterName -ErrorAction SilentlyContinue
        Write-Host "  ✓ Impresora eliminada" -ForegroundColor Green
    } else {
        Write-Host "  Instalación cancelada" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "[3/6] Creando puerto de impresora..." -ForegroundColor Yellow

try {
    # Verificar si el puerto ya existe
    $existingPort = Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue

    if ($existingPort) {
        Write-Host "  El puerto $PortName ya existe" -ForegroundColor Yellow
    } else {
        # Crear puerto (esto creará un puerto estándar, RedMon se configura después)
        Add-PrinterPort -Name $PortName -ErrorAction Stop
        Write-Host "  ✓ Puerto creado: $PortName" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR creando puerto: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/6] Instalando driver de impresora..." -ForegroundColor Yellow

try {
    # Verificar si el driver ya está instalado
    $existingDriver = Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue

    if ($existingDriver) {
        Write-Host "  ✓ Driver ya está instalado" -ForegroundColor Green
    } else {
        Add-PrinterDriver -Name $DriverName -ErrorAction Stop
        Write-Host "  ✓ Driver instalado: $DriverName" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR instalando driver: $_" -ForegroundColor Red
    Write-Host "  Intenta con un driver diferente o instálalo manualmente" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[5/6] Creando impresora..." -ForegroundColor Yellow

try {
    Add-Printer -Name $PrinterName -DriverName $DriverName -PortName $PortName -ErrorAction Stop
    Write-Host "  ✓ Impresora creada exitosamente: $PrinterName" -ForegroundColor Green
} catch {
    Write-Host "  ERROR creando impresora: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[6/6] Configuración de RedMon..." -ForegroundColor Yellow

# Determinar la ruta del script Python
if ($PythonScript -eq "") {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    $PythonScript = Join-Path $scriptDir "client\printer_driver\process_print.py"
}

if (Test-Path $PythonScript) {
    Write-Host "  ✓ Script encontrado: $PythonScript" -ForegroundColor Green
} else {
    Write-Host "  ADVERTENCIA: Script no encontrado: $PythonScript" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  IMPORTANTE: Configuración manual de RedMon requerida" -ForegroundColor Yellow
Write-Host "  ---------------------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Abre 'Dispositivos e impresoras'" -ForegroundColor White
Write-Host "  2. Click derecho en '$PrinterName' → Propiedades de la impresora" -ForegroundColor White
Write-Host "  3. Ve a la pestaña 'Puertos'" -ForegroundColor White
Write-Host "  4. Selecciona el puerto '$PortName' y click en 'Configurar puerto'" -ForegroundColor White
Write-Host "  5. En 'Redirect port to the program', escribe:" -ForegroundColor White
Write-Host ""
Write-Host "     python `"$PythonScript`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  6. En 'Arguments for this program', deja en blanco o escribe:" -ForegroundColor White
Write-Host ""
Write-Host "     %1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  7. En 'Output', selecciona 'Program handles output'" -ForegroundColor White
Write-Host "  8. Click OK y cierra las ventanas" -ForegroundColor White
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host " Instalación completada exitosamente" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "1. Completa la configuración manual de RedMon (ver arriba)" -ForegroundColor White
Write-Host "2. Inicia el monitor de impresión:" -ForegroundColor White
Write-Host "   python client\printer_driver\print_monitor.py" -ForegroundColor Cyan
Write-Host "3. Envía una impresión de prueba a '$PrinterName'" -ForegroundColor White
Write-Host ""
Write-Host "Para desinstalar, ejecuta: Remove-Printer -Name '$PrinterName'" -ForegroundColor Gray
Write-Host ""
