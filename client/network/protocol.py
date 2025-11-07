"""
Protocolo de comunicación del cliente
"""

from pathlib import Path
from typing import Dict, Any
import sys

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import create_print_job_message, Message
from shared.data_models import PrintParameters, PrintJobMetadata


def create_print_request(
    client_id: str,
    user: str,
    file_path: Path,
    parameters: PrintParameters,
    metadata: PrintJobMetadata
) -> Message:
    """
    Crea una petición de impresión

    Args:
        client_id: ID del cliente
        user: Usuario que solicita la impresión
        file_path: Ruta al archivo a imprimir
        parameters: Parámetros de impresión
        metadata: Metadatos del documento

    Returns:
        Mensaje de petición de impresión
    """
    # Leer el contenido del archivo
    with open(file_path, 'rb') as f:
        file_content = f.read()

    # Determinar formato del archivo
    file_format = file_path.suffix.lower().replace('.', '')

    return create_print_job_message(
        client_id=client_id,
        user=user,
        file_content=file_content,
        file_format=file_format,
        parameters=parameters.to_dict(),
        metadata=metadata.to_dict()
    )
