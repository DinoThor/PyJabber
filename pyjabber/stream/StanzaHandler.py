import xml.etree.ElementTree as ET

from loguru import logger

from pyjabber import metadata
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.JID import JID
from pyjabber.plugins.PluginManager import PluginManager

class InternalServerError(Exception):
    pass


class StanzaHandler:
    def __init__(self, buffer) -> None:
        self._host = metadata.host.get()
        self._buffer = buffer
        self._connections = ConnectionManager()
        self._message_queue = metadata.message_queue.get()

        self._peername = buffer.get_extra_info('peername')
        self._jid = self._connections.get_jid(self._peername)

        self._pluginManager = PluginManager(self._jid)
        self._presenceManager = Presence()

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

    def feed(self, element: ET.Element):
        try:
            self._functions[element.tag](element)
        except (KeyError, InternalServerError) as e:
            logger.error(e)
            logger.error(f"INTERNAL SERVER ERROR WITH {self._peername}. CLOSING CONNECTION FOR SERVER STABILITY")
            raise InternalServerError

    def handle_iq(self, element: ET.Element):
        """
            Process the iq stanza with the PluginManager (PM) class
            If the feature/XEP requested is not available, the PM instance
            will send a

            :param element: The stanza in the ElementTree format
        """
        res = self._pluginManager.feed(element)
        if res:
            self._buffer.write(res)

    def handle_msg(self, element: ET.Element):
        """
            Router the message to the client

            If the destination client is a user of a remote server, it will queue the message into the QueueMessage
            object and try to connect to the remote server

            :param element: the message in the ElementTree format
        """
        jid = JID(element.attrib["to"])

        if jid.domain == self._host:
            if not jid.resource:
                priority = self._presenceManager.most_priority(jid)
                if not priority:
                    self._message_queue.put_nowait(('MESSAGE', jid.bare(), ET.tostring(element)))
                    return None

                all_resources_online = []
                for user in priority:
                    all_resources_online += self._connections.get_buffer(JID(user=jid.user, domain=jid.domain, resource=user[0]))
                if not all_resources_online:
                    self._message_queue.put_nowait(('MESSAGE', jid.bare(), ET.tostring(element)))
                else:
                    for _, buffer in all_resources_online:
                        buffer.write(ET.tostring(element))
            else:
                resource_online = self._connections.get_buffer(jid)
                if not resource_online:
                    self._message_queue.put_nowait(('MESSAGE', str(jid), ET.tostring(element)))
                else:
                    for _, buffer in resource_online:
                        buffer.write(ET.tostring(element))

        else:
            pass
            # the s2s feature is currently disabled due to bad implementation
            # Future version of the server will fix that

            # server_buffer = self._connections.get_server_buffer(jid.bare())
            # if server_buffer:
            #     server_buffer[-1].write(ET.tostring(element))
            #
            # else:
            #     self._queue_message.enqueue(jid.domain, ET.tostring(element))

    def handle_pre(self, element: ET.Element):
        """
            Handle the presences stanzas
        """
        res = self._presenceManager.feed(self._jid, element)
        if res:
            self._buffer.write(res)
