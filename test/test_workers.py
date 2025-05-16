import asyncio
import os.path
import ssl
from ssl import SSLContext
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from pyjabber.network.XMLProtocol import TransportProxy
from pyjabber.stream.JID import JID
from pyjabber.workers import tls_worker, queue_worker


@pytest.mark.asyncio
async def test_tls_worker():
    with patch('pyjabber.workers.metadata') as mock_metadata, \
         patch('pyjabber.workers.asyncio.get_running_loop') as mock_get_loop, \
         patch('pyjabber.workers.ssl') as mock_ssl, \
         patch('pyjabber.workers.CertGenerator') as mock_cert:

        mock_queue = MagicMock()
        mock_transport = MagicMock()
        mock_protocol = MagicMock()
        mock_parser = MagicMock()

        mock_loop = MagicMock()
        mock_tls_return = MagicMock()
        mock_loop.start_tls.return_value = mock_tls_return
        mock_get_loop.return_value = mock_loop

        mock_transport.get_extra_info.return_value = ("127.0.0.1", "1234")

        mock_queue.get = AsyncMock()
        mock_queue.get.side_effect = [(mock_transport, mock_protocol, mock_parser), asyncio.CancelledError()]

        mock_metadata.TLS_QUEUE = mock_queue
        mock_metadata.CERT_PATH = os.path.dirname(os.path.abspath(__file__))
        mock_metadata.HOST = "localhost"

        mock_new_transport = MagicMock()
        mock_loop.start_tls = AsyncMock(return_value=mock_new_transport)

        mock_ssl.create_default_context.return_value = MagicMock()

        try:
            await asyncio.wait_for(tls_worker(), 3)
        except asyncio.TimeoutError:
            pytest.fail()

        mock_loop.start_tls.assert_called_once()
        kwargs = mock_loop.start_tls.call_args.kwargs
        assert kwargs["transport"] == mock_transport.originalTransport
        assert kwargs["protocol"] == mock_protocol
        assert kwargs["sslcontext"].maximum_version == mock_ssl.TLSVersion.TLSv1_2
        assert kwargs["sslcontext"].load_cert_chain.called

        assert type(mock_protocol.transport) == TransportProxy
        assert type(mock_parser.transport) == TransportProxy


@pytest.mark.asyncio
async def test_tls_worker_connection_error():
    with patch('pyjabber.workers.ConnectionManager') as mock_con, \
         patch('pyjabber.workers.metadata') as mock_metadata, \
         patch('pyjabber.workers.asyncio.get_running_loop') as mock_get_loop, \
         patch('pyjabber.workers.ssl') as mock_ssl, \
         patch('pyjabber.workers.logger') as mock_logger, \
         patch('pyjabber.workers.CertGenerator') as mock_cert:

        mock_queue = MagicMock()
        mock_transport = MagicMock()
        mock_protocol = MagicMock()
        mock_parser = MagicMock()

        mock_loop = MagicMock()
        mock_tls_return = MagicMock()
        mock_loop.start_tls.return_value = mock_tls_return
        mock_get_loop.return_value = mock_loop

        mock_peer = ("127.0.0.1", "1234")
        mock_transport.get_extra_info.return_value = mock_peer
        mock_transport.is_closing.return_value = False

        mock_queue.get = AsyncMock()
        mock_queue.get.side_effect = [(mock_transport, mock_protocol, mock_parser), asyncio.CancelledError()]

        mock_metadata.TLS_QUEUE = mock_queue
        mock_metadata.CERT_PATJ = ""
        mock_metadata.HOST = "localhost"

        mock_loop.start_tls = AsyncMock()
        mock_loop.start_tls.side_effect = ConnectionResetError()

        mock_ssl.create_default_context.return_value = MagicMock()

        try:
            await asyncio.wait_for(tls_worker(), 3)
        except asyncio.TimeoutError:
            pytest.fail()

        mock_loop.start_tls.assert_called_once()
        kwargs = mock_loop.start_tls.call_args.kwargs
        assert kwargs["transport"] == mock_transport.originalTransport
        assert kwargs["protocol"] == mock_protocol
        assert kwargs["sslcontext"].maximum_version == mock_ssl.TLSVersion.TLSv1_2
        assert kwargs["sslcontext"].load_cert_chain.called

        mock_logger.error.assert_called_once_with(f"ERROR DURING TLS UPGRADE WITH <{mock_peer}>")
        mock_con.return_value.close.assert_called_once_with(mock_peer)


@pytest.mark.skip
@pytest.mark.asyncio
async def test_tls_worker_connection_queue():
    with patch('pyjabber.workers.ConnectionManager') as mock_con, \
         patch('pyjabber.workers.metadata') as mock_metadata, \
         patch('pyjabber.workers.asyncio.get_running_loop') as mock_get_loop, \
         patch('pyjabber.workers.ssl') as mock_ssl, \
         patch('pyjabber.workers.logger') as mock_logger, \
         patch("pyjabber.workers.dict", return_value={"test@localhost": [b"message"]}):
        jid = JID('test@localhost')

        mock_con_queue = MagicMock()
        mock_con_queue.get = AsyncMock()
        mock_con_queue.get.side_effect = [('CONNECTION', jid)]


        mock_metadata.connection_queue.get.return_value = mock_con_queue
        mock_metadata.message_queue.get.return_value = AsyncMock()

        mock_metadata.connection_queue.get.side_effect = [('CONNECTION', jid)]

        await queue_worker()
