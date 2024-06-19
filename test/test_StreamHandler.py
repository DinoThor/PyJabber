from base64 import b64encode

import pytest
from unittest.mock import Mock, MagicMock, patch
from xml.etree import ElementTree as ET
from hashlib import sha256
from uuid import UUID
from pyjabber.utils import ClarkNotation as CN
from pyjabber.stream.StreamHandler import Stage, Signal, StreamHandler

def test_stage_enum():
    assert Stage.CONNECTED.value == 0
    assert Stage.OPENED.value == 1
    assert Stage.SSL.value == 2
    assert Stage.SASL.value == 3
    assert Stage.AUTH.value == 4
    assert Stage.BIND.value == 5
    assert Stage.READY.value == 6


def test_signal_enum():
    assert Signal.RESET.value == 0
    assert Signal.DONE.value == 1


def test_stream_handler_initialization():
    buffer = Mock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)

    assert handler._buffer == buffer
    assert handler._starttls == starttls
    assert handler._stage == Stage.CONNECTED
    assert handler._elem is None
    assert handler._jid is None


def test_stream_handler_buffer_property():
    buffer = Mock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)

    new_buffer = Mock()
    handler.buffer = new_buffer

    assert handler.buffer == new_buffer


def test_handle_open_stream_connected():
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)

    handler.handle_open_stream()

    assert handler._stage == Stage.OPENED
    buffer.write.assert_called_once()


def test_handle_open_stream_opened():
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)
    handler._stage = Stage.OPENED

    elem = ET.Element("starttls")
    result = handler.handle_open_stream(elem)

    assert handler._stage == Stage.SSL
    assert result == Signal.RESET
    buffer.write.assert_called_once()
    starttls.assert_called_once()


def test_handle_open_stream_ssl():
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)
    handler._stage = Stage.SSL

    handler.handle_open_stream()

    assert handler._stage == Stage.SASL
    buffer.write.assert_called_once()


from pyjabber.features.SASLFeature import SASL, connection

@patch('pyjabber.features.SASLFeature.connection')
@patch('pyjabber.stream.StreamHandler.SASL')
def test_handle_open_stream_sasl_continue(mock_sasl, mock_connection):
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)
    handler._stage = Stage.SASL

    password = b'password'
    keyhash = sha256(password).hexdigest()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (keyhash,)
    mock_conn.execute.return_value = mock_cursor
    mock_connection.return_value = mock_conn

    elem = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = b64encode(b'\x00username\x00password').decode('ascii')
    elem.text = auth_text

    # Ajustar la función _db_connection_factory para que tome un argumento
    def mock_db_connection_factory():
        return mock_conn

    sasl_instance = SASL(db_connection_factory=mock_db_connection_factory)
    sasl_instance._connections = MagicMock()
    mock_sasl.return_value = sasl_instance

    handler.handle_open_stream(elem)

    assert handler._stage == Stage.AUTH
    expected_response = b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
    buffer.write.assert_called_once_with(expected_response)
def test_handle_open_stream_auth():
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)
    handler._stage = Stage.AUTH

    handler.handle_open_stream()

    assert handler._stage == Stage.BIND
    buffer.write.assert_called_once()


def test_handle_open_stream_bind(monkeypatch):
    buffer = MagicMock()
    starttls = Mock()
    handler = StreamHandler(buffer, starttls)
    handler._stage = Stage.BIND

    iq_elem = ET.Element("iq", attrib={"type": "set", "id": "123"})
    bind_elem = ET.SubElement(iq_elem, CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind")))
    res_elem = ET.SubElement(bind_elem, CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "resource")))
    res_elem.text = "resource_id"

    connections = Mock()
    handler._connections = connections
    connections.get_jid_by_peer.return_value = "user"

    clark_notation_bind = CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind"))
    bind_elem_found = iq_elem.find(clark_notation_bind)
    assert bind_elem_found is not None, f"bind_elem_found should not be None, got {bind_elem_found}"

    result = handler.handle_open_stream(iq_elem)

    assert result == Signal.DONE
    buffer.write.assert_called_once()

    connections.get_jid_by_peer.assert_called_once_with(buffer.get_extra_info('peername'))
    connections.set_jid.assert_called_once_with(
        buffer.get_extra_info('peername'),
        'user@localhost/resource_id',
        buffer
    )

# Ejecutar los tests con pytest
if __name__ == "__main__":
    pytest.main()
