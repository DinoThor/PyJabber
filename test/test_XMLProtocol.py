import asyncio
from unittest.mock import MagicMock, patch
from xml import sax

import pytest

from pyjabber.network.protocols.XMLProtocol import XMLProtocol
from pyjabber.network.utils.Enums import ServerConnectionType as SCT


@pytest.fixture
def setup():
    with patch("pyjabber.network.protocols.XMLProtocol.XMLParser") as mock_parser:
        with patch("pyjabber.network.protocols.XMLProtocol.ConnectionManager") as mock_connection:
            with patch(
                "pyjabber.network.protocols.XMLProtocol.StreamAlivenessMonitor"
            ) as mock_monitor:
                with patch("pyjabber.network.protocols.XMLProtocol.Presence"):
                    with patch("pyjabber.network.protocols.XMLProtocol.AppConfig") as mock_config:
                        protocol = XMLProtocol(
                            namespace="jabber:client",
                            connection_timeout=30,
                        )
                        protocol._timeout_monitor = mock_monitor
                        yield protocol, mock_parser, mock_connection, mock_monitor


@patch("pyjabber.network.protocols.XMLProtocol.sax.make_parser")
@patch("pyjabber.network.protocols.XMLProtocol.TransportProxy")
def test_connection_made(TransportProxy, make_parser, setup):
    mock_transport = MagicMock()
    protocol, parser, connection, _ = setup
    protocol.connection_made(mock_transport)

    mock_transport.get_extra_info.assert_called_with("peername")
    make_parser.assert_called_once()
    make_parser().setFeature.assert_any_call(sax.handler.feature_namespaces, True)
    make_parser().setFeature.assert_any_call(sax.handler.feature_external_ges, False)
    make_parser().setContentHandler.assert_called_once_with(parser())
    connection().connection.assert_called_once_with(
        mock_transport.get_extra_info(), TransportProxy()
    )


def test_connection_lost(monkeypatch, setup):
    protocol, _, _, monitor = setup
    protocol._xml_parser = MagicMock()

    protocol.connection_lost(None)
    monitor.cancel.assert_called()
    assert protocol._transport is None
    assert protocol._xml_parser is None
    protocol._connection_manager.get_jid.assert_called_once()
    protocol._presence_manager.put_nowait.assert_called_once()


def test_data_received(setup):
    protocol, parser, _, monitor = setup
    protocol._xml_parser = parser
    data = b"<?xml version='1.0'?><stream:stream>"

    protocol.data_received(data)

    monitor.reset.assert_called_once()
    parser.feed.assert_called_once_with(b"<?xml version='1.0'?><stream:stream>")


def test_eof_received(setup):
    (
        protocol,
        _,
        _,
        _,
    ) = setup
    protocol._transport = MagicMock()
    with patch("pyjabber.network.protocols.XMLProtocol.logger") as mock_logger:
        protocol.eof_received()
        mock_logger.debug.assert_called()


def test_connection_timeout(setup):
    protocol, parser, _, monitor = setup

    mock_transport = MagicMock()
    mock_transport.is_closing.return_value = False
    protocol._transport = mock_transport
    with patch("pyjabber.network.protocols.XMLProtocol.logger") as mock_logger:
        protocol.connection_timeout()
        mock_logger.info.assert_called()
        mock_transport.write.assert_called_once_with(b"<connection-timeout/>")
        mock_transport.close.assert_called_once()
