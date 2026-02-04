import asyncio
import xml.etree.ElementTree as ET
from asyncio import Transport

from loguru import logger

from pyjabber import metadata
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN
from pyjabber.utils.Exceptions import InternalServerError


class StanzaHandler:
    def __init__(self, transport: Transport) -> None:
        self._ip = metadata.IP
        self._transport = transport
        self._connections = ConnectionManager()
        self._message_queue = metadata.MESSAGE_QUEUE
        self._message_persistence = metadata.MESSAGE_PERSISTENCE

        self._peername = transport.get_extra_info('peername')
        self._jid = self._connections.get_jid(self._peername)

        self._pluginManager = PluginManager(self._jid)
        self._presenceManager = Presence()

        self._connection_queue: asyncio.Queue = metadata.CONNECTION_QUEUE

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

    async def feed(self, element: ET.Element):
        try:
            await self._functions[element.tag](element)
        except (KeyError, InternalServerError) as e:
            logger.error(
                f"Internal server error {self._peername}. Closing connection for server stability. Reason: ${e}"
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

            If the destination client is a user of a remote server, it will queue the message into the QueueMessage
            object and try to connect to the remote server

            :param element: the message in the ElementTree format
        """
        jid = JID(element.attrib["to"])

        # Local bound
        if jid.domain == metadata.HOST or jid.domain in self._ip:
            if jid.domain in self._ip:
                jid.domain = metadata.HOST
            if not jid.resource:
                priority = self._presenceManager.most_priority(jid)
                if not priority and self._message_persistence:
                    await self._message_queue.put(
                        ('MESSAGE', JID(jid.bare()), ET.tostring(element))
                    )
                else:
                    all_resources_online = []
                    for user in priority:
                        buffer_online = self._connections.get_buffer_online(
                            JID(user=jid.user, domain=jid.domain, resource=user[0])
                        )
                        all_resources_online += buffer_online

                    for buffer in all_resources_online:
                        buffer[1].write(ET.tostring(element))

                return None
            else:
                resource_online = self._connections.get_buffer_online(jid)
                if not resource_online and self._message_persistence:
                    await self._message_queue.put(
                        ('MESSAGE', jid, ET.tostring(element))
                    )
                else:
                    for buffer in resource_online:
                        buffer[1].write(ET.tostring(element))
                return None

        # Remote server
        else:
            ns, tag = CN.deglose(element.tag)
            if ns == 'jabber:client':
                CN.update_namespace('jabber:server', element)

            buffer = self._connections.get_server_buffer(host=jid.domain)
            if buffer:
                buffer.write(ET.tostring(element))
            else:
                await self._message_queue.put(
                    ('MESSAGE', jid.domain, ET.tostring(element))
                )
            return None

    async def handle_pre(self, element: ET.Element):
        """
            Handle the presences stanzas
        """
        res = await self._presenceManager.feed(self._jid, element)
        if res:
            self._transport.write(res)
