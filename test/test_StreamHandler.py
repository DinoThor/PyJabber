import pytest
from unittest.mock import Mock, MagicMock, patch
from xml.etree import ElementTree as ET
from base64 import b64encode
from hashlib import sha256

from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN
from pyjabber.stream.StreamHandler import Stage, Signal, StreamHandler


@pytest.fixture
def setup():
    with patch('pyjabber.stream.StreamHandler.host') as mock_host:
        with patch('pyjabber.features.SASLFeature.host') as mock_host_sasl:
            buffer = Mock()
            starttls = Mock()
            mock_host.get.return_value = 'localhost'
            mock_host_sasl.get.return_value = 'localhost'
            return StreamHandler(buffer, starttls)


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


def test_stream_handler_initialization(setup):
    handler = setup

    assert handler._buffer is not None
    assert handler._starttls is not None
    assert handler._stage == Stage.CONNECTED
    assert handler._elem is None
    assert handler._jid is None

def test_stream_handler_buffer_property(setup):
    handler = setup

    new_buffer = Mock()
    handler.buffer = new_buffer

    assert handler.buffer == new_buffer

def test_handle_open_stream_connected(setup):
    handler = setup

    handler.handle_open_stream()

    assert handler._stage == Stage.OPENED
    handler._buffer.write.assert_called_once()

def test_handle_open_stream_opened(setup):
    handler = setup
    handler._stage = Stage.OPENED

    elem = ET.Element("starttls")
    result = handler.handle_open_stream(elem)

    assert handler._stage == Stage.SSL
    assert result == Signal.RESET
    handler._buffer.write.assert_called_once()
    handler._starttls.assert_called_once()

def test_handle_open_stream_ssl(setup):
    handler = setup
    handler._stage = Stage.SSL

    handler.handle_open_stream()

    assert handler._stage == Stage.SASL
    handler._buffer.write.assert_called_once()

from pyjabber.features.SASLFeature import SASL, connection


@patch('pyjabber.features.SASLFeature.connection')
def test_handle_open_stream_sasl_continue(mock_connection, setup):
    handler = setup
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

    with patch('pyjabber.features.SASLFeature.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        sasl_instance = SASL(db_connection_factory=mock_db_connection_factory)
        sasl_instance._connections = MagicMock()

        handler.handle_open_stream(elem)

    assert handler._stage == Stage.AUTH
    expected_response = b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
    handler._buffer.write.assert_called_once_with(expected_response)
def test_handle_open_stream_auth(setup):
    handler = setup
    handler._stage = Stage.AUTH

    handler.handle_open_stream()

    assert handler._stage == Stage.BIND
    handler._buffer.write.assert_called_once()

def test_handle_open_stream_bind(monkeypatch, setup):
    handler = setup
    handler._stage = Stage.BIND

    iq_elem = ET.Element("iq", attrib={"type": "set", "id": "123"})
    bind_elem = ET.SubElement(iq_elem, CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind")))
    res_elem = ET.SubElement(bind_elem, CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "resource")))
    res_elem.text = "resource_id"

    connections = Mock()
    handler._connection_manager = connections
    jid = JID("user@localhost")
    connections.get_jid.return_value = jid

    clark_notation_bind = CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind"))
    bind_elem_found = iq_elem.find(clark_notation_bind)
    assert bind_elem_found is not None, f"bind_elem_found should not be None, got {bind_elem_found}"

    result = handler.handle_open_stream(iq_elem)

    assert result == Signal.DONE
    handler._buffer.write.assert_called_once()

    connections.get_jid.assert_called_once_with(handler._buffer.get_extra_info('peername'))
    connections.set_jid.assert_called_once_with(
        handler._buffer.get_extra_info('peername'),
        jid,
        handler._buffer
    )

# Ejecutar los tests con pytest
if __name__ == "__main__":
    pytest.main()
