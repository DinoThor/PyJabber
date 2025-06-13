import asyncio
import os
import ssl
from typing import Dict, List

from loguru import logger

from pyjabber import metadata
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.ServerConnectionType import ServerConnectionType as SCT
from pyjabber.network.XMLProtocol import TransportProxy, XMLProtocol
from pyjabber.stream.JID import JID
from pyjabber.stream import Stream


async def tls_worker():
    """
    A TLS Worker for process STARTTLS petitions.
    A global Asyncio queue must be declared and used across the server. The main producer of the queue will be the
    XMLProtocol class, where the transport/buffer/protocol is managed.
    The worker is global for all the server components, and it can be duplicated across multiple workers in
    different threads to handle a high number of new connections established within a very short period of time.
    """
    connection_manager = ConnectionManager()

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.load_cert_chain(
        certfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_cert.pem"),
        keyfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_key.pem"),
    )

    server_ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    server_ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
    server_ssl_context.load_cert_chain(
        certfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_cert.pem"),
        keyfile=os.path.join(metadata.CERT_PATH, f"{metadata.HOST}_key.pem"),
    )

    server_ssl_context.check_hostname = False
    server_ssl_context.verify_mode = ssl.CERT_NONE

    loop = asyncio.get_running_loop()
    tls_queue = metadata.TLS_QUEUE
    try:
        while True:
            data = await tls_queue.get()

            if len(data) == 4:
                transport, protocol, parser, server_outgoing_host = data
                peer = transport.get_extra_info("peername")

                try:
                    server_host = connection_manager.get_server_host(peer)

                    new_transport = await loop.start_tls(
                        transport=transport.originalTransport,
                        protocol=protocol,
                        sslcontext=server_ssl_context,
                        server_hostname=server_host,
                        server_side=False)

                    new_transport = TransportProxy(new_transport, peer, True)
                    protocol.transport = new_transport
                    parser.transport = new_transport
                    connection_manager.update_transport_server(new_transport=new_transport, peer=peer)

                    logger.debug(f"Done TLS for <{peer}>")

                    initial_stream = Stream.Stream(
                        from_=metadata.HOST,
                        to="xmpp2.test",
                        xmlns=Stream.Namespaces.SERVER.value
                    ).open_tag()
                    new_transport.write(initial_stream)

                except ConnectionResetError as e:
                    logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
                    connection_manager.close_server(peer)

            else:
                transport, protocol, parser = data
                peer = transport.get_extra_info("peername")

                try:
                    new_transport = await loop.start_tls(
                        transport=transport.originalTransport,
                        protocol=protocol,
                        sslcontext=ssl_context,
                        server_side=True)

                    new_transport = TransportProxy(new_transport, peer, False)
                    protocol.transport = new_transport
                    parser.transport = new_transport
                    if protocol.namespace == 'jabber:client':
                        connection_manager.update_buffer(new_transport=new_transport, peer=peer)
                    else:
                        connection_manager.update_transport_server(new_transport=new_transport, peer=peer)

                    logger.debug(f"Done TLS for <{peer}>")

                except ConnectionResetError as e:
                    logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
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

    connection_queue: asyncio.Queue = metadata.CONNECTION_QUEUE
    message_queue: asyncio.Queue = metadata.MESSAGE_QUEUE
    server_queue: asyncio.Queue = metadata.S2S_OUTGOING_QUEUE

    try:
        while True:
            con_task = asyncio.create_task(connection_queue.get())
            msg_task = asyncio.create_task(message_queue.get())

            done, pending = await asyncio.wait(
                [con_task, msg_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            result = done.pop().result()

            if len(done) > 0:
                for item in done:
                    if item.result()[0] == 'CONNECTION':
                        connection_queue.put_nowait(item.result())
                    else:
                        message_queue.put_nowait(item.result())

            if result[0] == 'CONNECTION':
                _, jid = result

                if isinstance(jid, JID):
                    if str(jid) in pending_stanzas:
                        jid = str(jid)
                    elif jid.bare() in pending_stanzas:
                        jid = jid.bare()
                    else:
                        continue

                    if jid in pending_stanzas:
                        while pending_stanzas[jid]:
                            stanza_bytes = pending_stanzas[jid].pop()
                            buffer = connection_manager.get_buffer_online(JID(jid))
                            for b in buffer:
                                b[1].write(stanza_bytes)
                        pending_stanzas.pop(jid, None)

                else:
                    host = jid
                    if host in pending_stanzas:
                        while pending_stanzas[host]:
                            stanza_bytes = pending_stanzas[host].pop()
                            buffer = connection_manager.get_server_buffer(host=host)
                            buffer.write(stanza_bytes)
                        pending_stanzas.pop(host, None)

            else:
                _, jid, stanza_bytes = result
                if isinstance(jid, JID):
                    if jid.domain != metadata.HOST:
                        if jid.domain not in pending_stanzas:
                            pending_stanzas[jid.domain] = []
                        pending_stanzas[jid.domain].append(stanza_bytes)

                    else:
                        if str(jid) not in pending_stanzas:
                            pending_stanzas[str(jid)] = []
                        pending_stanzas[str(jid)].append(stanza_bytes)
                else:
                    host = jid
                    if host not in pending_stanzas:
                        pending_stanzas[host] = []
                    pending_stanzas[host].append(stanza_bytes)
                    server_queue.put_nowait(jid)

    except asyncio.CancelledError:
        pass


async def s2s_outgoing_connection_worker():
    connection_manager = ConnectionManager()
    s2s_queue: asyncio.Queue = metadata.S2S_OUTGOING_QUEUE
    loop = asyncio.get_running_loop()

    try:
        while True:
            host = await s2s_queue.get()

            already_open = connection_manager.get_server_buffer(host=host)
            if already_open:
                continue

            transport, _ = await loop.create_connection(
                lambda: XMLProtocol(
                    namespace="jabber:server",
                    host=host,
                    connection_timeout=metadata.CONNECTION_TIMEOUT,
                    cert_path=metadata.CERT_PATH,
                    connection_type=SCT.TO_SERVER
                ),
                host=host,
                port=metadata.SERVER_PORT,
                family=metadata.FAMILY
            )

    except asyncio.CancelledError:
        pass
