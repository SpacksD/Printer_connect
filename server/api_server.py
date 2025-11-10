"""
Servidor API REST para Printer_connect
Ejecuta la API FastAPI con uvicorn
"""

import sys
import argparse
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import uvicorn
except ImportError:
    print("ERROR: uvicorn no está instalado")
    print("Instala: pip install uvicorn[standard]")
    sys.exit(1)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Servidor API REST de Printer_connect'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host para escuchar (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Puerto para escuchar (default: 8080)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Auto-reload en cambios (desarrollo)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error'],
        help='Nivel de logging (default: info)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print(" Printer_connect - API REST Server")
    print(" Versión 0.5.0")
    print("=" * 60)
    print()
    print(f"Host: {args.host}")
    print(f"Puerto: {args.port}")
    print(f"Reload: {'Habilitado' if args.reload else 'Deshabilitado'}")
    print()
    print("Documentación interactiva:")
    print(f"  - Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"  - ReDoc: http://{args.host}:{args.port}/redoc")
    print()
    print("Presiona Ctrl+C para detener")
    print()

    # Configurar uvicorn
    uvicorn.run(
        "server.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True
    )


if __name__ == '__main__':
    main()
