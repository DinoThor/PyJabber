import asyncio
from typing import Dict, List, Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.AppConfig import app_config
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.queues.FailedRemoteConnection import FailedRemoteConnectionWrapper
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.PendingMessage import PendingMessageWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.stream.JID import JID


async def queue_worker():
    """
    Returns a coroutine that watches two different queues: one
    for new connections and another for new messages.

    - For the new connections queue, the worker checks if there are any pending
      messages in the buffer for the new connection's JID. If so, it processes
      them.
    - For the new messages queue, the worker directly enqueues incoming
      messages into the pending messages buffer.
    """
    local_pending_stanzas: Dict[str, List[bytes]] = {}
    remote_pending_stanzas: Dict[str, List[tuple[JID, bytes]]] = {}

    connection_manager = ConnectionManager()

    con_queue = get_queue(QueueName.CONNECTIONS)
    msg_queue = get_queue(QueueName.MESSAGES)
    s2s_queue = get_queue(QueueName.SERVERS)

    try:
        while True:
            con_task = asyncio.create_task(con_queue.get())
            msg_task = asyncio.create_task(msg_queue.get())

            done, pending = await asyncio.wait(
                [con_task, msg_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            result: Union[
                NewConnectionWrapper,
                PendingMessageWrapper,
                FailedRemoteConnectionWrapper,
            ] = done.pop().result()

            while done:
                item = done.pop().result()
                if isinstance(item, NewConnectionWrapper):
                    await con_queue.put(item)
                else:
                    await msg_queue.put(item)

            if isinstance(result, NewConnectionWrapper):
                if result.client:
                    jid: JID = result.value
                    jid_str = str(jid)
                    jid_bare = jid.bare()

                    target_key = (
                        jid_str
                        if jid_str in local_pending_stanzas
                        else (jid_bare if jid_bare in local_pending_stanzas else None)
                    )

                    if target_key:
                        stanzas_list = local_pending_stanzas[target_key]
                        buffer = connection_manager.get_transport_online(
                            JID(target_key)
                        )

                        while stanzas_list:
                            stanza_bytes = stanzas_list.pop()
                            for b in buffer:
                                b.transport.write(stanza_bytes)
                        local_pending_stanzas.pop(target_key, None)

                else:
                    host = result.value
                    if host in remote_pending_stanzas:
                        stanzas_list = remote_pending_stanzas[host]
                        buffer = connection_manager.get_server_transport_host(host)

                        while remote_pending_stanzas[host]:
                            _, stanza_bytes = stanzas_list.pop()
                            buffer.write(stanza_bytes)
                        remote_pending_stanzas.pop(host, None)

            elif isinstance(result, PendingMessageWrapper):
                jid = result.jid
                payload = result.payload

                if result.is_external:
                    if jid.domain not in remote_pending_stanzas:
                        remote_pending_stanzas[jid.domain] = []
                        await s2s_queue.put(
                            jid.domain
                        )  # Put remote host on connection queue

                    remote_pending_stanzas[jid.domain].append((jid, payload))
                else:
                    if str(jid) not in local_pending_stanzas:
                        local_pending_stanzas[str(jid)] = []
                    local_pending_stanzas[str(jid)].append(payload)

            else:  # FailedRemoteConnectionWrapper
                host = result.value
                error = ET.Element(
                    "error",
                    attrib={
                        "type": "cancel"
                        if result.reason == "remote-server-not-found"
                        else "wait"
                    },
                )

                if result.reason == "remote-server-not-found":
                    tag = "{urn:ietf:params:xml:ns:xmpp-stanzas}remote-server-not-found"
                else:
                    tag = "{urn:ietf:params:xml:ns:xmpp-stanzas}service-unavailable"

                ET.SubElement(error, tag)

                for jid, payload in remote_pending_stanzas[host]:
                    payload = ET.fromstring(payload)
                    payload.attrib["from"] = app_config.host
                    payload.attrib["to"] = str(jid)
                    payload.attrib["type"] = "error"
                    payload.attrib["id"] = str(uuid4())
                    payload.append(error)

                    for buffer in connection_manager.get_transport(jid):
                        buffer.transport.write(ET.tostring(payload))

                if result.reason == "remote-server-not-found":
                    remote_pending_stanzas.pop(host, None)

    except asyncio.CancelledError:
        pass
