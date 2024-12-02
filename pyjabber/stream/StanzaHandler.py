import os
import re
import xml.etree.ElementTree as ET
from uuid import uuid4

import loguru

from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.stream.QueueMessage import QueueMessage
from pyjabber.plugins.PluginManager import PluginManager


class InternalServerError(Exception):
    pass


class StanzaHandler:
    def __init__(self, host, buffer) -> None:
        self._host = host
        self._buffer = buffer
        self._connections = ConnectionManager()
        self._queue_message = QueueMessage()

        self._peername = buffer.get_extra_info('peername')
        self._jid = self._connections.get_jid(self._peername)

        self._pluginManager = PluginManager(self._jid)
        self._presenceManager = Presence(self._jid)

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

    def feed(self, element: ET.Element):
        try:
            self._functions[element.tag](element)
        except (KeyError, InternalServerError) as e:
            loguru.logger.error(e)
            loguru.logger.error(f"INTERNAL SERVER ERROR WITH {self._peername}. CLOSING CONNECTION FOR SERVER STABILITY")

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

        if re.match(fr'^[a-zA-Z0-9._%+-]+@{re.escape(self._host)}$', jid.bare()):
            for buffer in self._connections.get_buffer(JID(jid.bare())):
                buffer[-1].write(ET.tostring(element))

        else:
            server_buffer = self._connections.get_server_buffer(jid.bare())
            if server_buffer:
                server_buffer[-1].write(ET.tostring(element))

            else:
                self._queue_message.enqueue(jid.domain, ET.tostring(element))

    def handle_pre(self, element: ET.Element):
        res = self._presenceManager.feed(element, self._jid)
        if res:
            self._buffer.write(res)
