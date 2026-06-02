from base64 import b64encode
from hashlib import sha256
from unittest.mock import MagicMock, Mock, patch
from xml.etree import ElementTree as ET

import pytest

from pyjabber.features.Features import start_tls_feature
from pyjabber.stream.JID import JID
from pyjabber.stream.negotiators.StreamNegotiator import Signal, Stage, StreamNegotiator
from pyjabber.utils import ClarkNotation as CN


@pytest.fixture
def setup():
    with patch("pyjabber.stream.negotiators.StreamNegotiator.AppConfig") as mock_config:
        with patch("pyjabber.features.SASL.SASL.AppConfig") as mock_config_sasl:
            transport = Mock()
            mock_config.app_config.host = "localhost"
            mock_config.app_config.plugins = ["jabber:iq:register"]
            mock_config_sasl.app_config.host = "localhost"
            mock_protocol = MagicMock()
            mock_protocol.from_claim = None
            mock_parser = MagicMock()
            mock_handler = MagicMock()

            negotiator = StreamNegotiator(transport, mock_protocol, mock_parser, mock_handler)
            negotiator._stream_feature = MagicMock()
            yield negotiator

def test_stream_negotiator_initialization(setup):
    negotiator = setup

    assert negotiator._transport is not None
    assert negotiator._protocol is not None
    assert negotiator._parser is not None
    assert negotiator._handler is not None
    assert negotiator._stream_feature is not None
    assert negotiator._connection_manager is not None
    assert negotiator._ibr_feature is True
    assert negotiator._sasl is None
    assert negotiator._stages_handlers is not None
    assert negotiator._stage == Stage.CONNECTED
    negotiator._transport.get_extra_info.assert_called_once()



async def test_handle_open_stream_connected(setup):
    negotiator  = setup

    elem = ET.Element("{http://etherx.jabber.org/streams}stream")
    await negotiator.handle_open_stream(elem)

    assert negotiator._stage == Stage.OPENED
    negotiator._stream_feature.reset.assert_called_once()
    negotiator._stream_feature.register.assert_called_once()
    negotiator._transport.write.assert_called_once()


def test_handle_open_stream_opened(setup):
    negotiator = setup
    negotiator._stage = Stage.OPENED

    elem = ET.Element("starttls")
    result = negotiator.handle_open_stream(elem)

    assert negotiator._stage == Stage.SSL
    assert result == Signal.RESET
    negotiator._transport.write.assert_called_once()


def test_handle_open_stream_ssl(setup):
    negotiator = setup
    negotiator._stage = Stage.SSL

    negotiator.handle_open_stream()

    assert negotiator._stage == Stage.SASL
    assert negotiator._transport.write.call_count == 2


def test_handle_open_stream_sasl_continue(setup):
    negotiator = setup
    negotiator._stage = Stage.SASL

    password = b"password"
    keyhash = sha256(password).hexdigest()

    elem = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = b64encode(b"\x00username\x00password").decode("ascii")
    elem.text = auth_text

    with patch("pyjabber.stream.Streamnegotiator.SASL") as mock_sasl:
        mock_sasl.return_value.feed.return_value = (
            Signal.RESET,
            b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>",
        )
        negotiator.handle_open_stream(elem)

    assert negotiator._stage == Stage.AUTH
    expected_response = b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
    negotiator._transport.write.assert_called_once_with(expected_response)


def test_handle_open_stream_auth(setup):
    negotiator = setup
    negotiator._stage = Stage.AUTH

    negotiator.handle_open_stream()

    assert negotiator._stage == Stage.BIND
    negotiator._transport.write.assert_called_once()


def test_handle_open_stream_bind(monkeypatch, setup):
    negotiator = setup
    negotiator._stage = Stage.BIND

    iq_elem = ET.Element("iq", attrib={"type": "set", "id": "123"})
    bind_elem = ET.SubElement(
        iq_elem, CN.clark_from_tuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind"))
    )
    res_elem = ET.SubElement(
        bind_elem, CN.clark_from_tuple(("urn:ietf:params:xml:ns:xmpp-bind", "resource"))
    )
    res_elem.text = "resource_id"

    connections = Mock()
    negotiator._connection_manager = connections
    jid = JID("user@localhost")
    connections.get_jid.return_value = jid

    clark_notation_bind = CN.clark_from_tuple(
        ("urn:ietf:params:xml:ns:xmpp-bind", "bind")
    )
    bind_elem_found = iq_elem.find(clark_notation_bind)
    assert bind_elem_found is not None, (
        f"bind_elem_found should not be None, got {bind_elem_found}"
    )

    result = negotiator.handle_open_stream(iq_elem)

    assert result == Signal.DONE
    negotiator._transport.write.assert_called_once()

    connections.get_jid.assert_called_once_with(
        negotiator._transport.get_extra_info("peername")
    )
    connections.set_jid.assert_called_once_with(
        negotiator._transport.get_extra_info("peername"), jid, negotiator._transport
    )


# Ejecutar los tests con pytest
if __name__ == "__main__":
    pytest.main()
