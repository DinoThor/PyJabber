import asyncio
import xml.etree.ElementTree as ET
from asyncio import Transport

from loguru import logger

from pyjabber import AppConfig
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.PendingMessage import PendingMessageWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN
from pyjabber.utils.Exceptions import InternalServerError


class StanzaHandler:
    def __init__(self, transport: Transport) -> None:
        self._ip = AppConfig.app_config.ip
        self._transport = transport
        self._peername = transport.get_extra_info("peername")

        self._connections = ConnectionManager()
        self._jid = self._connections.get_jid(self._peername)

        self._pluginManager = PluginManager(self._jid)
        self._presenceManager = Presence()

        self._message_queue = get_queue(QueueName.MESSAGES)
        self._connection_queue: asyncio.Queue = get_queue(QueueName.CONNECTIONS)

        self._message_persistence = AppConfig.app_config.message_persistence

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre,
        }

        get_queue(QueueName.CONNECTIONS).put_nowait(NewConnectionWrapper(self._jid))

    async def feed(self, element: ET.Element):
        try:
            await self._functions[element.tag](element)
        except (KeyError, InternalServerError) as e:
            logger.error(
                f"Internal protocols error {self._peername}. Closing connection for protocols stability. Reason: ${e}"
            )
            raise InternalServerError

    async def handle_iq(self, element: ET.Element):
        """
        Process the iq stanza with the PluginManager (PM) class

        :param element: The stanza in the ElementTree format
        """
        res = await self._pluginManager.feed(element)
        if res:
            self._transport.write(res)

    async def handle_msg(self, element: ET.Element):
        """
        Router the message to the client

        If the destination client is a user of a remote protocols,
        it will queue the message into the QueueMessage
        object and try to connect to the remote protocols

        :param element: the message in the ElementTree format
        """
        jid = JID(element.attrib.get("to"))

        # Local bound
        if "from" not in element.attrib:
            element.attrib["from"] = str(self._jid)

        if jid.domain == AppConfig.app_config.host or jid.domain in self._ip:
            if jid.domain in self._ip:
                jid.domain = AppConfig.app_config.host
            if not jid.resource:
                priority = self._presenceManager.most_priority(jid)
                if not priority:
                    if self._message_persistence:
                        await self._message_queue.put(
                            PendingMessageWrapper(
                                jid=JID(jid.bare()), payload=ET.tostring(element)
                            )
                        )
                else:
                    all_resources_online = []
                    for user in priority:
                        buffer_online = self._connections.get_transport_online(
                            JID(user=jid.user, domain=jid.domain, resource=user[0])
                        )
                        all_resources_online += buffer_online

                    for buffer in all_resources_online:
                        buffer[1].write(ET.tostring(element))

            else:
                resource_online = self._connections.get_transport_online(jid)
                if not resource_online and self._message_persistence:
                    await self._message_queue.put(
                        PendingMessageWrapper(jid, ET.tostring(element))
                    )
                else:
                    for buffer in resource_online:
                        buffer[1].write(ET.tostring(element))

        # Remote protocols
        else:
            ns, tag = CN.break_down(element.tag)
            if ns == "jabber:client":
                CN.update_namespace("jabber:server", element)

            buffer = self._connections.get_server_transport_host(jid.domain)
            if buffer:
                buffer.write(ET.tostring(element))
            else:
                await self._message_queue.put(
                    PendingMessageWrapper(
                        jid, ET.tostring(element), external_host=jid.domain
                    )
                )

    async def handle_pre(self, element: ET.Element):
        """
        Handle the presences stanzas
        """
        res = await self._presenceManager.feed(self._jid, element)
        if res:
            self._transport.write(res)
