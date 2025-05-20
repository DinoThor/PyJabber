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
    with patch('pyjabber.stream.StreamHandler.metadata') as mock_meta_sh:
        with patch('pyjabber.features.SASLFeature.metadata') as mock_meta_sasl:
            transport = Mock()
            starttls = Mock()
            mock_meta_sh.HOST = 'localhost'
            mock_meta_sasl.HOST = 'localhost'
            yield StreamHandler(transport, starttls)


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

    assert handler._transport is not None
    assert handler._starttls is not None
    assert handler._stage == Stage.CONNECTED

def test_stream_handler_transport_property(setup):
    handler = setup

    new_transport = Mock()
    handler.transport = new_transport

    assert handler.transport == new_transport

def test_handle_open_stream_connected(setup):
    handler = setup

    handler.handle_open_stream()

    assert handler._stage == Stage.OPENED
    handler._transport.write.assert_called_once()

def test_handle_open_stream_opened(setup):
    handler = setup
    handler._stage = Stage.OPENED

    elem = ET.Element("starttls")
    result = handler.handle_open_stream(elem)

    assert handler._stage == Stage.SSL
    assert result == Signal.RESET
    handler._transport.write.assert_called_once()
    handler._starttls.assert_called_once()

def test_handle_open_stream_ssl(setup):
    handler = setup
    handler._stage = Stage.SSL

    handler.handle_open_stream()

    assert handler._stage == Stage.SASL
    handler._transport.write.assert_called_once()

from pyjabber.features.SASLFeature import SASL, SASLFeature


def test_handle_open_stream_sasl_continue(setup):
    handler = setup
    handler._stage = Stage.SASL

    password = b'password'
    keyhash = sha256(password).hexdigest()

    elem = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = b64encode(b'\x00username\x00password').decode('ascii')
    elem.text = auth_text

    with patch.object(SASL, "__init__", lambda self: None), \
         patch.object(SASL, "feed", return_value=(Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")):

         handler.handle_open_stream(elem)

    assert handler._stage == Stage.AUTH
    expected_response = b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
    handler._transport.write.assert_called_once_with(expected_response)


def test_handle_open_stream_auth(setup):
    handler = setup
    handler._stage = Stage.AUTH

    handler.handle_open_stream()

    assert handler._stage == Stage.BIND
    handler._transport.write.assert_called_once()

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
    handler._transport.write.assert_called_once()

    connections.get_jid.assert_called_once_with(handler._transport.get_extra_info('peername'))
    connections.set_jid.assert_called_once_with(
        handler._transport.get_extra_info('peername'),
        jid,
        handler._transport
    )

# Ejecutar los tests con pytest
if __name__ == "__main__":
    pytest.main()
