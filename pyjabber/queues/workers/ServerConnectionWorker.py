import asyncio
import socket

from loguru import logger

from pyjabber import AppConfig
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.protocols.XMLProtocolServerOutgoing import (
    XMLProtocolServerOutgoing,
)
from pyjabber.queues.FailedRemoteConnection import FailedRemoteConnectionWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue


async def server_connection_worker():
    """
    Returns a coroutine that watches a queue for connection requests to
    external servers (S2S).
    """
    server_queue = get_queue(QueueName.SERVERS)
    connection_queue = get_queue(QueueName.CONNECTIONS)
    connection_manager = ConnectionManager()
    loop = asyncio.get_running_loop()

    try:
        while True:
            host = await server_queue.get()

            already_open = connection_manager.get_server_transport_host(host)
            if already_open:
                continue

            await loop.create_connection(
                lambda: XMLProtocolServerOutgoing(
                    namespace="jabber:server",
                    host=host,
                    connection_timeout=AppConfig.app_config.connection_timeout,
                ),
                host=host,
                port=AppConfig.app_config.server_port,
                family=AppConfig.app_config.family,
            )

    except asyncio.CancelledError:
        pass

    except (ConnectionRefusedError, asyncio.TimeoutError):
        logger.info(f"Remote server <{host}> rejected connection")
        await connection_queue.put(
            FailedRemoteConnectionWrapper(value=host, reason="service-unavailable")
        )

    except socket.gaierror:
        logger.info(f"Remote server <{host}> not found in the DNS lookup")
        await connection_queue.put(
            FailedRemoteConnectionWrapper(value=host, reason="remote-server-not-found")
        )
