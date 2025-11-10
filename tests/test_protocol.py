"""
Tests para el protocolo de comunicación
"""

import pytest
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.protocol import Message, Protocol, create_print_job_message, create_response_message
from shared.constants import MESSAGE_TYPE_PRINT_JOB, MESSAGE_TYPE_RESPONSE


class TestMessage:
    """Tests para la clase Message"""

    def test_message_creation(self):
        """Test creación de mensaje básico"""
        data = {'test': 'value'}
        message = Message(message_type='test', data=data)

        assert message.message_type == 'test'
        assert message.data == data
        assert message.timestamp is not None

    def test_message_to_dict(self):
        """Test conversión a diccionario"""
        data = {'key': 'value'}
        message = Message(message_type='test', data=data)
        msg_dict = message.to_dict()

        assert 'version' in msg_dict
        assert 'message_type' in msg_dict
        assert 'timestamp' in msg_dict
        assert 'data' in msg_dict
        assert msg_dict['data'] == data

    def test_message_to_json(self):
        """Test serialización a JSON"""
        data = {'test': 'value'}
        message = Message(message_type='test', data=data)
        json_str = message.to_json()

        assert isinstance(json_str, str)
        assert 'test' in json_str
        assert 'value' in json_str

    def test_message_from_json(self):
        """Test deserialización desde JSON"""
        data = {'test': 'value'}
        message = Message(message_type='test', data=data)
        json_str = message.to_json()

        # Deserializar
        restored_message = Message.from_json(json_str)

        assert restored_message.message_type == message.message_type
        assert restored_message.data == message.data


class TestProtocol:
    """Tests para la clase Protocol"""

    def test_encode_decode_message(self):
        """Test codificación y decodificación de mensajes"""
        data = {'test': 'value', 'number': 123}
        message = Message(message_type='test', data=data)

        # Codificar
        encoded = Protocol.encode_message(message)
        assert isinstance(encoded, bytes)
        assert len(encoded) > 4  # Al menos el header de longitud

        # Decodificar
        decoded = Protocol.decode_message(encoded)
        assert decoded.message_type == message.message_type
        assert decoded.data == message.data

    def test_encode_decode_with_unicode(self):
        """Test con caracteres Unicode"""
        data = {'text': 'Hola, ¿cómo estás? 你好'}
        message = Message(message_type='test', data=data)

        encoded = Protocol.encode_message(message)
        decoded = Protocol.decode_message(encoded)

        assert decoded.data['text'] == data['text']


class TestHelperFunctions:
    """Tests para funciones helper"""

    def test_create_print_job_message(self):
        """Test creación de mensaje de trabajo de impresión"""
        file_content = b'Test PDF content'
        parameters = {'page_size': 'A4'}
        metadata = {'document_name': 'test.pdf'}

        message = create_print_job_message(
            client_id='TEST-001',
            user='test_user',
            file_content=file_content,
            file_format='pdf',
            parameters=parameters,
            metadata=metadata
        )

        assert message.message_type == MESSAGE_TYPE_PRINT_JOB
        assert message.data['client_id'] == 'TEST-001'
        assert message.data['user'] == 'test_user'
        assert message.data['file_format'] == 'pdf'
        assert 'file_content' in message.data  # Base64 encoded

    def test_create_response_message(self):
        """Test creación de mensaje de respuesta"""
        message = create_response_message(
            status='success',
            message='Job received',
            job_id='JOB-001',
            queue_position=1
        )

        assert message.message_type == MESSAGE_TYPE_RESPONSE
        assert message.data['status'] == 'success'
        assert message.data['message'] == 'Job received'
        assert message.data['job_id'] == 'JOB-001'
        assert message.data['queue_position'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
