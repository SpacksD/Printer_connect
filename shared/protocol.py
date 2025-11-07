"""
Protocolo de comunicación entre cliente y servidor
Define el formato de mensajes y la serialización/deserialización
"""

import json
import struct
from datetime import datetime
from typing import Dict, Any, Optional
from .constants import (
    PROTOCOL_VERSION,
    MESSAGE_TYPE_PRINT_JOB,
    MESSAGE_TYPE_RESPONSE,
    BUFFER_SIZE,
)


class Message:
    """Clase base para mensajes del protocolo"""

    def __init__(
        self,
        message_type: str,
        data: Dict[str, Any],
        version: str = PROTOCOL_VERSION
    ):
        """
        Inicializa un mensaje

        Args:
            message_type: Tipo de mensaje
            data: Datos del mensaje
            version: Versión del protocolo
        """
        self.version = version
        self.message_type = message_type
        self.timestamp = datetime.now().isoformat()
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el mensaje a diccionario"""
        return {
            'version': self.version,
            'message_type': self.message_type,
            'timestamp': self.timestamp,
            'data': self.data
        }

    def to_json(self) -> str:
        """Serializa el mensaje a JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        Deserializa un mensaje desde JSON

        Args:
            json_str: String JSON

        Returns:
            Mensaje deserializado
        """
        data_dict = json.loads(json_str)
        return cls(
            message_type=data_dict['message_type'],
            data=data_dict['data'],
            version=data_dict.get('version', PROTOCOL_VERSION)
        )

    def __repr__(self) -> str:
        return f"Message(type={self.message_type}, version={self.version})"


class Protocol:
    """Maneja la serialización y deserialización de mensajes"""

    @staticmethod
    def encode_message(message: Message) -> bytes:
        """
        Codifica un mensaje para envío por red

        Formato:
        - 4 bytes: longitud del mensaje (unsigned int)
        - N bytes: mensaje JSON en UTF-8

        Args:
            message: Mensaje a codificar

        Returns:
            Bytes codificados
        """
        json_str = message.to_json()
        json_bytes = json_str.encode('utf-8')
        length = len(json_bytes)

        # Empaquetar longitud (4 bytes, unsigned int, big-endian) + mensaje
        return struct.pack('!I', length) + json_bytes

    @staticmethod
    def decode_message(data: bytes) -> Message:
        """
        Decodifica un mensaje desde bytes

        Args:
            data: Bytes recibidos

        Returns:
            Mensaje decodificado
        """
        # Desempaquetar longitud
        if len(data) < 4:
            raise ValueError("Datos insuficientes para decodificar mensaje")

        length = struct.unpack('!I', data[:4])[0]

        # Extraer mensaje JSON
        json_bytes = data[4:4+length]
        json_str = json_bytes.decode('utf-8')

        return Message.from_json(json_str)

    @staticmethod
    def receive_full_message(sock, buffer_size: int = BUFFER_SIZE) -> Optional[bytes]:
        """
        Recibe un mensaje completo desde un socket

        Args:
            sock: Socket desde el cual recibir
            buffer_size: Tamaño del buffer

        Returns:
            Mensaje completo en bytes, o None si la conexión se cerró
        """
        # Primero recibir los 4 bytes de longitud
        length_data = b''
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                return None  # Conexión cerrada
            length_data += chunk

        # Obtener la longitud del mensaje
        message_length = struct.unpack('!I', length_data)[0]

        # Recibir el mensaje completo
        message_data = b''
        while len(message_data) < message_length:
            chunk = sock.recv(min(buffer_size, message_length - len(message_data)))
            if not chunk:
                return None  # Conexión cerrada
            message_data += chunk

        # Retornar longitud + mensaje
        return length_data + message_data


def create_print_job_message(
    client_id: str,
    user: str,
    file_content: bytes,
    file_format: str,
    parameters: Dict[str, Any],
    metadata: Dict[str, Any]
) -> Message:
    """
    Crea un mensaje de trabajo de impresión

    Args:
        client_id: ID del cliente
        user: Usuario que solicita la impresión
        file_content: Contenido del archivo en bytes
        file_format: Formato del archivo (pdf, postscript, etc.)
        parameters: Parámetros de impresión
        metadata: Metadatos del documento

    Returns:
        Mensaje de trabajo de impresión
    """
    import base64

    data = {
        'client_id': client_id,
        'user': user,
        'file_content': base64.b64encode(file_content).decode('ascii'),
        'file_format': file_format,
        'parameters': parameters,
        'metadata': metadata
    }

    return Message(message_type=MESSAGE_TYPE_PRINT_JOB, data=data)


def create_response_message(
    status: str,
    message: str,
    job_id: Optional[str] = None,
    queue_position: Optional[int] = None,
    error_code: Optional[str] = None
) -> Message:
    """
    Crea un mensaje de respuesta del servidor

    Args:
        status: Estado de la respuesta (success/error)
        message: Mensaje descriptivo
        job_id: ID del trabajo (opcional)
        queue_position: Posición en cola (opcional)
        error_code: Código de error (opcional)

    Returns:
        Mensaje de respuesta
    """
    data = {
        'status': status,
        'message': message,
        'job_id': job_id,
        'queue_position': queue_position,
        'error_code': error_code
    }

    return Message(message_type=MESSAGE_TYPE_RESPONSE, data=data)
