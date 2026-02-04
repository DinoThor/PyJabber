import asyncio
from typing import Dict, List

from pyjabber import metadata
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.utils.Enums import ServerConnectionType as SCT
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.stream.JID import JID


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
