import pickle
import xml.etree.ElementTree as ET

import xmlschema

from pyjabber.features.PresenceFeature import Presence
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.stanzas.Message import Message
from pyjabber.utils import ClarkNotation as CN

class StanzaHandler():
    def __init__(self, buffer) -> None:
        self._buffer        = buffer
        self._connections   = ConectionsManager()
        self._peername      = buffer.get_extra_info('peername')
        self._jid           = self._connections.get_jid_by_peer(self._peername)
        self._pluginManager = PluginManager(self._jid)

        self._functions     = {
            "{jabber:client}iq"          : self.handleIQ,
            "{jabber:client}message"     : self.handleMsg,
            "{jabber:client}presence"    : self.handlePre
        }

        self._PresenceManager = Presence()
        
        with open("./pyjabber/schemas/schemas.pkl", "rb") as schemasDump:
            self._schemas = pickle.load(schemasDump)

    def feed(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[0]]
            if schema.is_valid(ET.tostring(element)) is False:
                raise Exception()   #Invalid stanza
        except KeyError:
            raise Exception()

        try:
            self._functions[element.tag](element)
        except KeyError:
            raise Exception()
        
    ############################################################
    ############################################################

    def handleIQ(self, element: ET.Element):
        res = self._pluginManager.feed(element)
        if res:
            for r in res:
                self._buffer.write(r)

    def handleMsg(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[0]]
            if schema.is_valid(ET.tostring(element)) is False:
                raise Exception()   #Invalid stanza
        except KeyError:
            raise Exception()
        
        reciverBuffer = self._connections.get_buffer_by_jid(element.attrib["to"])
        for buffer in reciverBuffer:
            buffer.write(ET.tostring(element))

    def handlePre(self, element: ET.Element):
        if "type" in element.attrib.keys():
            # if element.attrib["type"] == "subscribe":
            res = self._PresenceManager.feed(element, self._jid)
            if res:
                self._buffer.write(res)

