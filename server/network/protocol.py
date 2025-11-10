"""
Protocolo de comunicación del servidor
"""

import base64
from typing import Dict, Any
from pathlib import Path
import sys

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.protocol import create_response_message, Message
from shared.data_models import PrintParameters, PrintJobMetadata


def parse_print_job(message: Message) -> Dict[str, Any]:
    """
    Parsea un mensaje de trabajo de impresión

    Args:
        message: Mensaje recibido

    Returns:
        Diccionario con los datos del trabajo de impresión
    """
    data = message.data

    # Decodificar el contenido del archivo
    file_content = base64.b64decode(data['file_content'])

    # Parsear parámetros y metadatos
    parameters = PrintParameters.from_dict(data['parameters'])
    metadata = PrintJobMetadata.from_dict(data['metadata'])

    return {
        'client_id': data['client_id'],
        'user': data['user'],
        'file_content': file_content,
        'file_format': data['file_format'],
        'parameters': parameters,
        'metadata': metadata
    }


def create_success_response(
    message: str,
    job_id: str,
    queue_position: int = 1
) -> Message:
    """
    Crea una respuesta de éxito

    Args:
        message: Mensaje descriptivo
        job_id: ID del trabajo
        queue_position: Posición en la cola

    Returns:
        Mensaje de respuesta exitosa
    """
    return create_response_message(
        status='success',
        message=message,
        job_id=job_id,
        queue_position=queue_position
    )


def create_error_response(
    message: str,
    error_code: str = 'UNKNOWN_ERROR'
) -> Message:
    """
    Crea una respuesta de error

    Args:
        message: Mensaje descriptivo del error
        error_code: Código de error

    Returns:
        Mensaje de respuesta con error
    """
    return create_response_message(
        status='error',
        message=message,
        error_code=error_code
    )
