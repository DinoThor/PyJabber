import asyncio
import os
import queue
import ssl

from loguru import logger
from xml.etree import ElementTree as ET

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.XMLProtocol import TransportProxy


async def tls_worker(loop: asyncio.AbstractEventLoop, tls_queue: queue.Queue, cert_path: str, host: str):
    """
    A TLS Worker for process STARTTLS petitions.
    A global Asyncio queue must be declared and used across the server. The main producer of the queue will be the
    XMLProtocol class, where the transport/buffer/protocol is managed.
    The worker is global for all the server components, and it can be duplicated across multiple workers in
    different threads to handle a high number of new connections established within a very short period of time.

    :param loop:
    :param tls_queue: The global queue used ONLY for (TRANSPORT, PROTOCOL, PARSER) tuples
    :param tls_queue:
    :param cert_path:
    :param host:
    """
    connection_manager = ConnectionManager()
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(
        certfile=os.path.join(cert_path, f"{host}_cert.pem"),
        keyfile=os.path.join(cert_path, f"{host}_key.pem"),
    )
    loop = asyncio.get_running_loop()
    try:
        while True:
            transport, protocol, parser = await tls_queue.get()
            peer = transport.get_extra_info("peername")
            try:
                new_transport = await loop.start_tls(
                    transport=transport.originalTransport,
                    protocol=protocol,
                    sslcontext=ssl_context,
                    server_side=True)

                new_transport = TransportProxy(new_transport, peer)
                transport = new_transport
                parser.buffer = new_transport
                logger.debug(f"Done TLS for <{peer}>")

            except ConnectionResetError:
                logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
                if not transport.is_closing():
                    connection_manager.close(peer)
    except asyncio.CancelledError:
        pass


async def queue_worker(
    loop: asyncio.AbstractEventLoop,
    message: ET.Element,
    connection_queue: asyncio.Queue,
    message_queue: asyncio.Queue
):
    try:
        while True:
            con_task = asyncio.create_task(connection_queue.get())
            msg_task = asyncio.create_task(message_queue.get())

            done, pending = await asyncio.wait(
                [con_task, msg_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            result = done.pop().result()

            for task in pending:
                task.cancel()

            if len(done) > 1:
                for item in done:
                    if item.result()[0] == 'CONNECTION':
                        connection_queue.put_nowait(item)
                    else:
                        message_queue.put_nowait(item)

            if result[0] == 'CONNECTION':
                pass
            else:
                pass

    except asyncio.CancelledError:
        pass
