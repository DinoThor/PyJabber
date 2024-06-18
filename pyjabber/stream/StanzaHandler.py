import os
import pickle
import re
import xml.etree.ElementTree as ET

import xmlschema

from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class StanzaHandler:
    def __init__(self, buffer, connection_manager) -> None:
        self._buffer = buffer
        self._connections = connection_manager
        self._peername = buffer.get_extra_info('peername')
        self._jid = self._connections.get_jid(self._peername)

        self._pluginManager = PluginManager(self._jid)
        self._presenceManager = Presence(self._jid, self._connections)

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

        with open(FILE_PATH + "/schemas/schemas.pkl", "rb") as schemasDump:
            self._schemas = pickle.load(schemasDump)

    def feed(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[0]]
            if schema.is_valid(ET.tostring(element)) is False:
                self._buffer.write(SE.bad_request())
        except KeyError:
            self._buffer.write(SE.feature_not_implemented())

        try:
            self._functions[element.tag](element)
        except KeyError:
            raise Exception()

    ############################################################
    ############################################################

    def handle_iq(self, element: ET.Element):
        res = self._pluginManager.feed(element)
        if res:
            self._buffer.write(res)

    def handle_msg(self, element: ET.Element):
        bare_jid = element.attrib["to"].split("/")[0]

        if re.match(r'^.+@localhost$', bare_jid):
            for buffer in self._connections.get_buffer(bare_jid):
                buffer[-1].write(ET.tostring(element))

        else:
            server_buffer = self._connections.get_server_buffer(bare_jid)

    def handle_pre(self, element: ET.Element):
        res = self._presenceManager.feed(element, self._jid)
        if res:
            self._buffer.write(res)
