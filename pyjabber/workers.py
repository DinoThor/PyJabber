import asyncio
import os
import ssl
from typing import Dict, List

from loguru import logger

from pyjabber import metadata
from pyjabber.network import CertGenerator
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.XMLProtocol import TransportProxy
from pyjabber.stream.JID import JID


async def tls_worker():
    """
    A TLS Worker for process STARTTLS petitions.
    A global Asyncio queue must be declared and used across the server. The main producer of the queue will be the
    XMLProtocol class, where the transport/buffer/protocol is managed.
    The worker is global for all the server components, and it can be duplicated across multiple workers in
    different threads to handle a high number of new connections established within a very short period of time.
    """
    try:
        if CertGenerator.check_hostname_cert_exists(metadata.HOST, metadata.CERT_PATH) is False:
            CertGenerator.generate_hostname_cert(metadata.HOST, metadata.CERT_PATH)
    except FileNotFoundError as e:
        logger.error(f"{e.__class__.__name__}: Pass an existing directory in your system to load the certs. "
                     f"Closing server")
        raise SystemExit

    connection_manager = ConnectionManager()
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.load_cert_chain(
        certfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_cert.pem"),
        keyfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_key.pem"),
    )
    loop = asyncio.get_running_loop()
    tls_queue = metadata.TLS_QUEUE
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
                protocol.transport = new_transport
                parser.transport = new_transport
                logger.debug(f"Done TLS for <{peer}>")

            except ConnectionResetError:
                logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
                if not transport.is_closing():
                    connection_manager.close(peer)
    except asyncio.CancelledError:
        pass


async def queue_worker():
    """
       Creates a worker in the asyncio loop that accepts two different queues: one
       for new connections and another for new messages. The worker continuously
       reads from both queues.

       - For the new connections queue, the worker checks if there are any pending
         messages in the buffer for the new connection's JID. If so, it processes
         them.
       - For the new messages queue, the worker directly enqueues incoming
         messages into the pending messages buffer.

       Returns:
           None: This function does not return a value; it runs indefinitely in an
           asynchronous loop.
   """
    pending_stanzas: Dict[str, List[bytes]] = {}
    connection_manager = ConnectionManager()
    connection_queue = metadata.CONNECTION_QUEUE
    message_queue = metadata.MESSAGE_QUEUE

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
                _, jid = result

                if str(jid) in pending_stanzas:
                    jid = str(jid)
                elif jid.bare() in pending_stanzas:
                    jid = jid.bare()
                else:
                    jid = None

                while jid and pending_stanzas[jid]:
                    stanza_bytes = pending_stanzas[jid].pop()
                    buffer = connection_manager.get_buffer_online(JID(jid))
                    for b in buffer:
                        b[1].write(stanza_bytes)

            else:
                _, jid, stanza_bytes = result
                if str(jid) not in pending_stanzas:
                    pending_stanzas[str(jid)] = []
                pending_stanzas[str(jid)].append(stanza_bytes)

    except asyncio.CancelledError:
        pass
