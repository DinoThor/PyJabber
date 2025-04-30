import asyncio
import ssl
from ssl import SSLContext
from unittest.mock import patch, MagicMock

import pytest

from pyjabber.workers import tls_worker

@pytest.skip
@pytest.mark.asyncio
async def test_tls_worker():
    with patch('pyjabber.workers.ConnectionManager') as mock_con, \
         patch('pyjabber.workers.ConnectionManager.metadata') as mock_metadata, \
         patch('pyjabber.workers.ConnectionManager.asyncio.get_running_loop') as mock_get_loop, \
         patch('pyjabber.workers.os') as mock_os:
        

        mock_queue = MagicMock()
        mock_transport = MagicMock()
        mock_protocol = MagicMock()
        mock_parser = MagicMock()

        mock_loop = MagicMock()
        mock_tls_return = MagicMock()
        mock_loop.start_tls.return_value = mock_tls_return
        mock_get_loop.return_value = mock_loop

        mock_transport.get_extra_info.return_value = ("127.0.0.1", "1234")

        mock_queue.return_value = {mock_transport, mock_protocol, mock_parser}
        mock_metadata.tls_queue.get.return_value = mock_queue

        await asyncio.wait_for(tls_worker(), 1)

        mock_loop.start_tls.assert_called_once()
        args = mock_loop.start_tls.call_args.args
        assert args[0] == mock_transport
        assert args[1] == mock_protocol
        assert args[3] is True

        sslcontext: SSLContext = args[2]

        assert sslcontext.maximum_version == ssl.TLSVersion.TLSv1_2
        assert


