import pytest
from unittest.mock import MagicMock, patch
from pyjabber.network.server.incoming.XMLServerIncomingProtocol import XMLServerIncomingProtocol
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor


@pytest.fixture
def setup_protocol():
    namespace = 'namespace'
    host = 'host'
    connection_timeout = 10
    connection_manager = MagicMock()
    cert_path = 'cert_path'
    queue_message = MagicMock()
    protocol = XMLServerIncomingProtocol(
        namespace,
        host,
        connection_timeout,
        connection_manager,
        cert_path,
        queue_message
    )
    return protocol, connection_manager


def test_initialization(setup_protocol):
    protocol, connection_manager = setup_protocol
    assert protocol._host == 'host'
    assert protocol._connection_timeout == 10
    assert protocol._connection_manager == connection_manager
    assert protocol._queue_message is not None


@patch('xml.sax.make_parser', return_value=MagicMock())
def test_connection_made_with_transport(mock_make_parser, setup_protocol):
    protocol, connection_manager = setup_protocol
    transport = MagicMock()
    transport.get_extra_info.return_value = 'peername'

    protocol.connection_made(transport)

    assert protocol._transport == transport
    mock_make_parser.return_value.setContentHandler.assert_called()
    connection_manager.connection.assert_called_with('peername')
    assert protocol._timeout_monitor is not None

@patch('xml.sax.make_parser', return_value=MagicMock())
def test_connection_made_without_transport(mock_make_parser, setup_protocol):
    protocol, connection_manager = setup_protocol
    transport = None

    with patch('pyjabber.network.server.incoming.XMLServerIncomingProtocol.logger') as mock_logger:
        protocol.connection_made(transport)
        mock_logger.error.assert_called_with("Invalid transport")


def test_eof_received(setup_protocol):
    protocol, connection_manager = setup_protocol
    transport = MagicMock()
    transport.get_extra_info.return_value = 'peername'
    protocol._transport = transport
    protocol._xml_parser = MagicMock()

    protocol.eof_received()

    connection_manager.disconnection_server.assert_called_with('peername')
    assert protocol._transport is None
    assert protocol._xml_parser is None


@patch('xml.sax.make_parser', return_value=MagicMock())
def test_connection_made_with_timeout_monitor(mock_make_parser, setup_protocol):
    protocol, connection_manager = setup_protocol
    transport = MagicMock()
    transport.get_extra_info.return_value = 'peername'

    protocol.connection_made(transport)

    assert isinstance(protocol._timeout_monitor, StreamAlivenessMonitor)


if __name__ == "__main__":
    pytest.main()
