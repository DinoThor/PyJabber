import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from xml import sax
import ssl
from pyjabber.network.XMLProtocol import XMLProtocol, FILE_AUTH
import os


@patch('pyjabber.network.XMLProtocol.sax.make_parser')
@patch('pyjabber.network.XMLProtocol.ConnectionManager')
def test_connection_made(mock_connections_manager, mock_make_parser):
    mock_transport = MagicMock()
    mock_parser = MagicMock()
    mock_make_parser.return_value = mock_parser
    mock_handler = MagicMock()

    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = mock_connections_manager.return_value
    traefik_certs = False
    queue_message = MagicMock()

    with patch('pyjabber.network.XMLProtocol.XMLParser', return_value=mock_handler):
        protocol = XMLProtocol(
            namespace=namespace,
            connection_timeout=connection_timeout,
            connection_manager=connection_manager,
            traefik_certs=traefik_certs,
            queue_message=queue_message
        )
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

    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    with patch('pyjabber.network.XMLProtocol.sax.make_parser', return_value=mock_parser):
        protocol = XMLProtocol(
            namespace=namespace,
            connection_timeout=connection_timeout,
            connection_manager=connection_manager,
            traefik_certs=traefik_certs,
            queue_message=queue_message
        )
        protocol.connection_made(mock_transport)

    mock_monitor.assert_called_once_with(timeout=30, callback=protocol.connection_timeout)
    mock_transport.get_extra_info.assert_called_with('peername')


def test_connection_lost():
    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    protocol = XMLProtocol(
        namespace=namespace,
        connection_timeout=connection_timeout,
        connection_manager=connection_manager,
        traefik_certs=traefik_certs,
        queue_message=queue_message
    )
    mock_transport = MagicMock()
    protocol._transport = mock_transport

    protocol.connection_lost(None)
    mock_transport.get_extra_info.assert_called_with('peername')
    assert protocol._transport is None
    assert protocol._xml_parser is None


def test_data_received():
    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    protocol = XMLProtocol(
        namespace=namespace,
        connection_timeout=connection_timeout,
        connection_manager=connection_manager,
        traefik_certs=traefik_certs,
        queue_message=queue_message
    )
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_parser = MagicMock()
    protocol._xml_parser = mock_parser
    mock_monitor = MagicMock()
    protocol._timeout_monitor = mock_monitor

    data = b"<?xml version=\'1.0\'?><stream:stream>"
    protocol.data_received(data)
    mock_monitor.reset.assert_called_once()
    mock_parser.feed.assert_called_once_with(b"<stream:stream>")


def test_eof_received():
    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    protocol = XMLProtocol(
        namespace=namespace,
        connection_timeout=connection_timeout,
        connection_manager=connection_manager,
        traefik_certs=traefik_certs,
        queue_message=queue_message
    )
    mock_transport = MagicMock()
    protocol.connection_made(mock_transport)
    mock_connections = MagicMock()
    protocol._connection_manager = mock_connections

    protocol.eof_received()
    mock_transport.get_extra_info.assert_called_with('peername')
    mock_connections.disconnection.assert_called_once_with(mock_transport.get_extra_info.return_value)

    # Verificar que el transporte y el analizador XML se mantengan en su estado actual
    assert protocol._transport == mock_transport
    assert protocol._xml_parser is not None  # El parser debe estar inicializado en connection_made



def test_connection_timeout():
    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    protocol = XMLProtocol(
        namespace=namespace,
        connection_timeout=connection_timeout,
        connection_manager=connection_manager,
        traefik_certs=traefik_certs,
        queue_message=queue_message
    )
    mock_transport = MagicMock()
    protocol._transport = mock_transport

    protocol.connection_timeout()
    mock_transport.get_extra_info.assert_called_with('peername')
    mock_transport.write.assert_called_once_with(b"<connection-timeout/>")
    mock_transport.close.assert_called_once()
    assert protocol._transport is None
    assert protocol._xml_parser is None


@patch('pyjabber.network.XMLProtocol.asyncio.get_running_loop')
@patch('pyjabber.network.XMLProtocol.ssl.create_default_context')
def test_enable_tls(mock_create_default_context, mock_get_running_loop):
    namespace = "jabber:client"
    connection_timeout = 30
    connection_manager = MagicMock()
    traefik_certs = False
    queue_message = MagicMock()

    protocol = XMLProtocol(
        namespace=namespace,
        connection_timeout=connection_timeout,
        connection_manager=connection_manager,
        traefik_certs=traefik_certs,
        queue_message=queue_message
    )
    mock_transport = MagicMock()
    protocol._transport = mock_transport
    mock_loop = MagicMock()
    mock_get_running_loop.return_value = mock_loop

    # Crear un contexto SSL real para evitar el error isinstance
    real_ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    mock_create_default_context.return_value = real_ssl_context

    # Mockear el parser para evitar el error 'NoneType'
    mock_parser = MagicMock()
    protocol._xml_parser = mock_parser

    # Asegurarse de que start_tls es un AsyncMock
    mock_loop.start_tls = AsyncMock()

    async def run_enable_tls():
        await protocol.enable_tls()
        mock_create_default_context.assert_called_once_with(ssl.Purpose.CLIENT_AUTH)
        real_ssl_context.load_cert_chain.assert_called_once_with(
            certfile=os.path.join(FILE_AUTH, 'certs', 'localhost.pem'),
            keyfile=os.path.join(FILE_AUTH, 'certs', 'localhost-key.pem')
        )
        mock_loop.start_tls.assert_called_once_with(
            transport=mock_transport,
            protocol=protocol,
            sslcontext=real_ssl_context,
            server_side=True
        )

    mock_loop.run_until_complete(run_enable_tls())

