# Investigación: Impresora Virtual en Windows

## Fecha: 2025-11-07
## Fase: 2 - Impresora Virtual

---

## Objetivo

Implementar un sistema de captura de trabajos de impresión en Windows que:
1. Actúe como una impresora instalada en el sistema
2. Capture todos los trabajos enviados a ella
3. Convierta los trabajos a PDF
4. Envíe automáticamente al servidor

---

## Opciones Evaluadas

### Opción 1: GhostScript + RedMon ⭐ **SELECCIONADA**

**Descripción:**
- RedMon (Redirection Port Monitor) intercepta trabajos de impresión
- GhostScript convierte PostScript a PDF
- Python procesa el PDF resultante

**Ventajas:**
- ✅ No requiere desarrollo de drivers kernel
- ✅ Componentes maduros y estables
- ✅ Fácil instalación
- ✅ Buena documentación
- ✅ Gratuito y open source

**Desventajas:**
- ⚠️ Requiere instalación de componentes externos
- ⚠️ Configuración manual inicial

**Componentes:**
- GhostScript: https://www.ghostscript.com/
- RedMon: http://pages.cs.wisc.edu/~ghost/redmon/
- Python script para procesamiento

### Opción 2: Microsoft Universal Print Driver + Port Monitor

**Descripción:**
- Usar Universal Print Driver de Windows
- Desarrollar Port Monitor personalizado en C++

**Ventajas:**
- ✅ Integración nativa con Windows
- ✅ No requiere componentes de terceros

**Desventajas:**
- ❌ Requiere desarrollo en C++
- ❌ Requiere firma de drivers (certificado costoso)
- ❌ Complejidad alta
- ❌ Tiempo de desarrollo largo

### Opción 3: Windows Printing API + Spooler

**Descripción:**
- Usar win32print para crear impresora
- Monitorear el spooler directamente

**Ventajas:**
- ✅ Todo en Python
- ✅ API bien documentada

**Desventajas:**
- ❌ Menos control sobre el proceso
- ❌ Posibles problemas con diferentes aplicaciones
- ❌ Complejidad en manejo de formatos

### Opción 4: CUPS-PDF (adaptado para Windows)

**Descripción:**
- Portar CUPS-PDF a Windows

**Desventajas:**
- ❌ CUPS es principalmente para Linux/Unix
- ❌ Requiere mucho trabajo de adaptación

---

## Decisión: GhostScript + RedMon

Esta opción ofrece el mejor balance entre funcionalidad, facilidad de implementación y mantenibilidad.

---

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────┐
│           Aplicación del Usuario                        │
│           (Word, Excel, Chrome, etc.)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Imprime a "Printer_connect"
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Windows Print Spooler                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Envía a Puerto "RPT1:"
                     ▼
┌─────────────────────────────────────────────────────────┐
│           RedMon (Port Monitor)                         │
│           - Intercepta el trabajo                       │
│           - Ejecuta script configurado                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Ejecuta: process_print.py
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Python Script (process_print.py)              │
│           - Recibe PostScript en stdin                  │
│           - Llama a GhostScript                         │
│           - Convierte a PDF                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ PDF generado
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Cliente Printer_connect                       │
│           - Lee el PDF                                  │
│           - Extrae parámetros                           │
│           - Envía al servidor                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ TCP/IP (JSON)
                     ▼
              [Servidor Printer_connect]
```

---

## Pasos de Implementación

### 1. Instalación de Componentes (Manual)

**GhostScript:**
```powershell
# Descargar de https://www.ghostscript.com/download/gsdnld.html
# Instalar ejecutable
# Agregar a PATH: C:\Program Files\gs\gs10.02.0\bin
```

**RedMon:**
```powershell
# Descargar de http://pages.cs.wisc.edu/~ghost/redmon/
# Instalar ejecutable (redmon19.exe)
# Requiere permisos de administrador
```

### 2. Configuración de Impresora

**Script PowerShell para crear impresora:**
```powershell
# Agregar puerto RedMon
Add-PrinterPort -Name "RPT1:" -PrinterHostAddress "localhost"

# Instalar driver PostScript genérico
Add-PrinterDriver -Name "MS Publisher Color Printer"

# Crear impresora
Add-Printer -Name "Printer_connect" `
    -DriverName "MS Publisher Color Printer" `
    -PortName "RPT1:"

# Configurar RedMon para ejecutar script Python
# Esto se hace manualmente en las propiedades del puerto
```

### 3. Script de Procesamiento

**process_print.py:**
- Lee PostScript desde stdin
- Convierte a PDF usando GhostScript
- Guarda en carpeta temporal
- Notifica al cliente principal

### 4. Monitoreo de Carpeta

**Cliente monitorea carpeta:**
- Usa `watchdog` para detectar nuevos PDFs
- Procesa automáticamente
- Envía al servidor

---

## Extracción de Parámetros

### Desde el Job de Impresión

**Parámetros disponibles:**
- Tamaño de página (del PostScript)
- Orientación (del PostScript)
- Número de páginas (conteo al convertir)
- Usuario (del proceso de Windows)
- Aplicación origen (del proceso)

**Usando win32print:**
```python
import win32print

def get_job_info(printer_name, job_id):
    handle = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.GetJob(handle, job_id, 1)
        return {
            'user': job['pUserName'],
            'document': job['pDocument'],
            'pages': job['TotalPages'],
            'submitted': job['Submitted']
        }
    finally:
        win32print.ClosePrinter(handle)
```

### Desde el PostScript

**Parser de comentarios DSC:**
```python
def parse_postscript_params(ps_file):
    params = {}
    with open(ps_file, 'rb') as f:
        for line in f:
            line = line.decode('latin-1', errors='ignore')
            if line.startswith('%%BoundingBox:'):
                # Extraer tamaño de página
                pass
            elif line.startswith('%%Orientation:'):
                # Extraer orientación
                pass
    return params
```

---

## Conversión PostScript a PDF

### Usando GhostScript

**Comando básico:**
```bash
gswin64c.exe ^
    -dNOPAUSE ^
    -dBATCH ^
    -sDEVICE=pdfwrite ^
    -sOutputFile=output.pdf ^
    input.ps
```

**Parámetros de calidad:**
```bash
-dPDFSETTINGS=/printer    # Calidad de impresión
-dColorConversionStrategy=/RGB
-dAutoRotatePages=/None
```

**Wrapper Python:**
```python
import subprocess

def convert_ps_to_pdf(ps_file, pdf_file):
    gs_command = [
        'gswin64c.exe',
        '-dNOPAUSE',
        '-dBATCH',
        '-sDEVICE=pdfwrite',
        '-dPDFSETTINGS=/printer',
        f'-sOutputFile={pdf_file}',
        ps_file
    ]

    subprocess.run(gs_command, check=True)
```

---

## Formatos de Entrada Soportados

### PostScript (.ps)
- Formato estándar de impresión
- La mayoría de aplicaciones lo generan
- Conversión directa con GhostScript

### XPS (XML Paper Specification)
- Formato moderno de Windows
- Requiere conversión adicional
- Opción: xpstopdf o usar API de Windows

### EMF (Enhanced Metafile)
- Formato gráfico de Windows
- Más complejo de manejar
- Requiere API de Windows para conversión

---

## Instalador Automatizado

### Script de Instalación (PowerShell)

**install_printer.ps1:**
```powershell
# Verificar si es administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Error "Este script requiere permisos de administrador"
    exit 1
}

# Verificar GhostScript
$gsPath = "C:\Program Files\gs\gs10.02.0\bin\gswin64c.exe"
if (-not (Test-Path $gsPath)) {
    Write-Error "GhostScript no está instalado"
    exit 1
}

# Verificar RedMon
$redmonPath = "$env:SystemRoot\System32\redmon39.dll"
if (-not (Test-Path $redmonPath)) {
    Write-Error "RedMon no está instalado"
    exit 1
}

# Crear puerto
Add-PrinterPort -Name "RPT1:" -PrinterHostAddress "localhost"

# Agregar driver
Add-PrinterDriver -Name "MS Publisher Color Printer"

# Crear impresora
Add-Printer -Name "Printer_connect" `
    -DriverName "MS Publisher Color Printer" `
    -PortName "RPT1:"

Write-Host "Impresora instalada exitosamente"
```

---

## Testing

### Test en Entorno Real

**Aplicaciones a probar:**
- Microsoft Word
- Adobe Acrobat Reader
- Google Chrome
- Notepad
- Excel

**Escenarios:**
- Diferentes tamaños de página
- Múltiples copias
- Orientación portrait/landscape
- Documentos multipágina
- Documentos con imágenes

### Test Automatizado

**Simulación de trabajos:**
```python
def simulate_print_job(pdf_file):
    """Simula un trabajo de impresión sin hardware"""
    # Convierte PDF a PostScript
    # Procesa con el script
    # Verifica que se envíe al servidor
```

---

## Limitaciones Conocidas

1. **Requiere instalación manual de GhostScript y RedMon**
   - Solución: Incluir en instalador

2. **Configuración de RedMon es manual**
   - Solución: Script PowerShell para automatizar

3. **Algunos formatos requieren conversión adicional**
   - Solución: Agregar convertidores adicionales

4. **Parámetros de impresión pueden perderse**
   - Solución: Parsear PostScript DSC comments

---

## Seguridad

### Consideraciones

1. **Script ejecutado por Print Spooler**
   - Corre con permisos del sistema
   - Validar todos los inputs

2. **Archivos temporales**
   - Usar carpeta segura
   - Limpiar después de procesar

3. **Información sensible**
   - Los documentos pueden contener información confidencial
   - Implementar encriptación en tránsito

---

## Alternativas para Futuro

### Si GhostScript + RedMon no funciona bien:

1. **Desarrollar Port Monitor nativo**
   - Mayor control
   - Sin dependencias externas
   - Requiere inversión significativa

2. **Usar Microsoft Print to PDF**
   - Monitorear carpeta de salida
   - Menos control sobre el proceso

3. **Integración con servicios en la nube**
   - Google Cloud Print (descontinuado)
   - Microsoft Universal Print

---

## Cronograma

- **Semana 1**: Setup de GhostScript + RedMon, pruebas manuales
- **Semana 2**: Script de procesamiento Python
- **Semana 3**: Integración con cliente existente
- **Semana 4**: Instalador automatizado y testing

---

## Recursos

- [GhostScript Documentation](https://www.ghostscript.com/doc/current/Use.htm)
- [RedMon Documentation](http://pages.cs.wisc.edu/~ghost/redmon/)
- [Windows Printing API](https://learn.microsoft.com/en-us/windows/win32/printdocs/printing-and-print-spooler)
- [PostScript Language Reference](https://www.adobe.com/products/postscript/pdfs/PLRM.pdf)

---

## Conclusión

La combinación de **GhostScript + RedMon + Python** ofrece una solución robusta y relativamente simple para implementar la impresora virtual en Windows. Aunque requiere componentes externos, estos son maduros y bien documentados, lo que reduce el riesgo de implementación.

La arquitectura propuesta permite:
- ✅ Captura transparente de trabajos de impresión
- ✅ Conversión automática a PDF
- ✅ Integración fluida con el cliente existente
- ✅ Mantenibilidad a largo plazo

---

**Preparado por**: Claude (Anthropic)
**Fecha**: 2025-11-07
**Estado**: Aprobado para implementación
