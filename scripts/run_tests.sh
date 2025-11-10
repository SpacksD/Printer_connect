#!/bin/bash
# Script para ejecutar todos los tests con cobertura

echo "================================"
echo " Printer_connect - Test Suite"
echo "================================"
echo

# Verificar que pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest no está instalado"
    echo "   Instala: pip install pytest pytest-cov"
    exit 1
fi

# Directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Ejecutando tests..."
echo

# Ejecutar tests con cobertura
pytest tests/ \
    -v \
    --cov=server \
    --cov=client \
    --cov=shared \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml

RESULT=$?

echo
echo "================================"
echo " Resultado de Tests"
echo "================================"

if [ $RESULT -eq 0 ]; then
    echo "✅ Todos los tests pasaron"
    echo
    echo "Reportes de cobertura:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - XML: coverage.xml"
    echo
    echo "Ver reporte HTML:"
    echo "  xdg-open htmlcov/index.html  # Linux"
    echo "  open htmlcov/index.html      # macOS"
    echo "  start htmlcov/index.html     # Windows"
else
    echo "❌ Algunos tests fallaron"
    exit 1
fi
