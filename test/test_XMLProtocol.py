import asyncio
from unittest.mock import MagicMock, patch,AsyncMock
import pytest
from xml import sax
import ssl
from pyjabber.network.XMLProtocol import XMLProtocol, FILE_AUTH
import os


@patch('pyjabber.network.XMLProtocol.sax.make_parser')
@patch('pyjabber.network.XMLProtocol.ConectionsManager')
def test_connection_made(mock_connections_manager, mock_make_parser):
    mock_transport = MagicMock()
    mock_parser = MagicMock()
    mock_make_parser.return_value = mock_parser
    mock_handler = MagicMock()

    with patch('pyjabber.network.XMLProtocol.XMPPStreamHandler', return_value=mock_handler):
        protocol = XMLProtocol(connection_timeout=30)
        protocol.connection_made(mock_transport)

    mock_transport.get_extra_info.assert_called_with('peername')
    mock_make_parser.assert_called_once()
    mock_parser.setFeature.assert_any_call(sax.handler.feature_namespaces, True)
    mock_parser.setFeature.assert_any_call(sax.handler.feature_external_ges, False)
    mock_parser.setContentHandler.assert_called_once_with(mock_handler)
    mock_connections_manager.return_value.connection.assert_called_once_with(mock_transport.get_extra_info.return_value)


@patch('pyjabber.network.XMLProtocol.StreamAlivenessMonitor')
def test_connection_made_with_timeout(mock_monitor):
    mock_transport = MagicMock()
    mock_parser = MagicMock()

    with patch('pyjabber.network.XMLProtocol.sax.make_parser', return_value=mock_parser):
        protocol = XMLProtocol(connection_timeout=30)
        protocol.connection_made(mock_transport)

    mock_monitor.assert_called_once_with(timeout=30, callback=protocol.connection_timeout)
    mock_transport.get_extra_info.assert_called_with('peername')


def test_connection_lost():
    protocol = XMLProtocol()
    mock_transport = MagicMock()
    protocol._transport = mock_transport

    protocol.connection_lost(None)
    mock_transport.get_extra_info.assert_called_with('peername')
    assert protocol._transport is None
    assert protocol._xml_parser is None


def test_data_received():
    protocol = XMLProtocol(connection_timeout=30)
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_parser = MagicMock()
    protocol._xml_parser = mock_parser
    mock_monitor = MagicMock()
    protocol._timeout_monitor = mock_monitor

    data = b"<?xml version=\"1.0\"?><stream:stream>"
    protocol.data_received(data)
    mock_monitor.reset.assert_called_once()
    mock_parser.feed.assert_called_once_with(b"<stream:stream>")


def test_eof_received():
    protocol = XMLProtocol()
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_connections = MagicMock()
    protocol._connections = mock_connections

    protocol.eof_received()
    mock_transport.get_extra_info.assert_called_with('peername')
    mock_connections.disconnection.assert_called_once_with(mock_transport.get_extra_info.return_value)
    assert protocol._transport is None
    assert protocol._xml_parser is None


def test_connection_timeout():
    protocol = XMLProtocol()
    mock_transport = MagicMock()
    protocol._transport = mock_transport

    protocol.connection_timeout()
    mock_transport.get_extra_info.assert_called_with('peername')
    mock_transport.write.assert_called_once_with(b"<connection-timeout/>")
    mock_transport.close.assert_called_once()
    assert protocol._transport is None
    assert protocol._xml_parser is None



@pytest.mark.asyncio
@patch('pyjabber.network.XMLProtocol.asyncio.get_running_loop')
async def test_taskTLS(mock_get_running_loop):
    protocol = XMLProtocol()
    mock_loop = MagicMock()
    mock_get_running_loop.return_value = mock_loop

    enableTLS_coroutine = AsyncMock()

    with patch.object(XMLProtocol, 'enableTLS', return_value=enableTLS_coroutine):
        protocol.taskTLS()

    mock_loop.create_task.assert_called_once()
    called_coroutine = mock_loop.create_task.call_args[0][0]
    assert asyncio.iscoroutine(called_coroutine)
    assert called_coroutine.__name__ == enableTLS_coroutine().__name__
    mock_loop.create_task.return_value.add_done_callback.assert_called_once_with(protocol.handleSTARTTLS)

    # Espera a que la coroutine simulada sea llamada y esperada
    await called_coroutine

@patch('pyjabber.network.XMLProtocol.asyncio.get_running_loop')
@patch('pyjabber.network.XMLProtocol.ssl.SSLContext')
def test_enableTLS(mock_ssl_context, mock_get_running_loop):
    protocol = XMLProtocol()
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_loop = MagicMock()
    mock_get_running_loop.return_value = mock_loop
    mock_ssl = MagicMock()
    mock_ssl_context.return_value = mock_ssl

    # Asegurarse de que start_tls es un AsyncMock
    mock_loop.start_tls = AsyncMock()

    async def run_enableTLS():
        await protocol.enableTLS()
        mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLSv1_2)
        mock_ssl.load_cert_chain.assert_called_once_with(
            os.path.join(FILE_AUTH, 'certs', 'localhost.pem'),
            os.path.join(FILE_AUTH, 'certs', 'localhost-key.pem')
        )
        mock_loop.start_tls.assert_called_once_with(
            transport=mock_transport,
            protocol=mock_transport.get_protocol(),
            sslcontext=mock_ssl,
            server_side=True
        )

    asyncio.run(run_enableTLS())

@patch('pyjabber.network.XMLProtocol.asyncio.get_running_loop')
@patch('pyjabber.network.XMLProtocol.ssl.SSLContext')
def test_handleSTARTTLS(mock_ssl_context, mock_get_running_loop):
    protocol = XMLProtocol()
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_parser = MagicMock()
    protocol._xml_parser = mock_parser
    mock_handler = MagicMock()
    mock_parser.getContentHandler.return_value = mock_handler

    mock_task = MagicMock()
    mock_task.result.return_value = mock_transport

    protocol.handleSTARTTLS(mock_task)
    assert protocol._transport == mock_transport
    mock_handler.buffer = mock_transport
    assert mock_handler.buffer == mock_transport
