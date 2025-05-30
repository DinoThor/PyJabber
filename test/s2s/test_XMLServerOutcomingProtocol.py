import pytest
from unittest.mock import MagicMock, patch
import asyncio
import ssl
from pyjabber.network.server.outgoing.XMLServerOutcomingProtocol import XMLServerOutcomingProtocol
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor

@pytest.fixture
def setup_protocol():
    namespace = 'namespace'
    host = 'example.com'
    public_host = 'public.example.com'
    connection_timeout = 10
    connection_manager = MagicMock()
    queue_message = MagicMock()
    protocol = XMLServerOutcomingProtocol(
        namespace,
        host,
        public_host,
        connection_timeout,
        connection_manager,
        queue_message
    )
    return protocol, connection_manager

def test_initialization(setup_protocol):
    protocol, connection_manager = setup_protocol
    assert protocol._host == 'example.com'
    assert protocol._public_host == 'public.example.com'
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
    connection_manager.connection_server.assert_called_with('peername', protocol._host, transport)
    assert isinstance(protocol._timeout_monitor, StreamAlivenessMonitor)

@patch('xml.sax.make_parser', return_value=MagicMock())
def test_connection_made_without_transport(mock_make_parser, setup_protocol):
    protocol, _ = setup_protocol
    transport = None

    with patch('pyjabber.network.server.outgoing.XMLServerOutcomingProtocol.logger') as mock_logger:
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


@pytest.mark.asyncio
async def test_enable_tls(setup_protocol):
    protocol, _ = setup_protocol
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_loop = MagicMock(spec=asyncio.AbstractEventLoop)
    mock_new_transport = MagicMock()
    mock_loop.start_tls.return_value = mock_new_transport

    # Simular connection_made para inicializar _xml_parser
    with patch('xml.sax.make_parser', return_value=MagicMock()) as mock_make_parser:
        protocol.connection_made(mock_transport)

    mock_ssl_context = MagicMock()
    with patch('ssl.create_default_context', return_value=mock_ssl_context) as mock_create_context:
        await protocol.enable_tls(mock_loop)

        mock_loop.start_tls.assert_called_once()
        assert protocol._transport == mock_new_transport

        # Verificar que OP_NO_TLSv1_3 no se ha añadido a las opciones
        mock_ssl_context.options.__ior__.assert_not_called()


@pytest.mark.asyncio
async def test_enable_tls_no_tls1_3(setup_protocol):
    protocol, _ = setup_protocol
    protocol._enable_tls1_3 = False
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_loop = MagicMock(spec=asyncio.AbstractEventLoop)
    mock_new_transport = MagicMock()
    mock_loop.start_tls.return_value = mock_new_transport

    # Simular connection_made para inicializar _xml_parser
    with patch('xml.sax.make_parser', return_value=MagicMock()) as mock_make_parser:
        protocol.connection_made(mock_transport)

    mock_ssl_context = MagicMock()
    mock_ssl_context.options = 0  # Inicializar options como un entero

    with patch('ssl.create_default_context', return_value=mock_ssl_context) as mock_create_context:
        await protocol.enable_tls(mock_loop)

        mock_loop.start_tls.assert_called_once()
        assert protocol._transport == mock_new_transport

        # Verificar que OP_NO_TLSv1_3 se ha añadido a las opciones
        assert mock_ssl_context.options & ssl.OP_NO_TLSv1_3 == ssl.OP_NO_TLSv1_3
if __name__ == "__main__":
    pytest.main()
