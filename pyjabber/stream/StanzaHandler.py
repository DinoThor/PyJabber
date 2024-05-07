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
        peername = buffer.get_extra_info('peername')
        print(peername)
        
        
        self._buffer        = buffer
        self._connections   = ConectionsManager()
        self._pluginManager = PluginManager(self._connections.get_jid(peername))

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
            self._buffer.write(res)

    def handleMsg(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[0]]
            if schema.is_valid(ET.tostring(element)) is False:
                raise Exception()   #Invalid stanza
        except KeyError:
            raise Exception()
        
        reciverBuffer = self._connections.get_buffer_by_jid(element.attrib["to"])
        res = Message(
            mto     = element.attrib["to"],
            mfrom   = element.attrib["from"],
            id      = element.attrib["id"],
            body    = element.find(CN.clarkFromTuple(("jabber:client", "body"))).text
        ) 
        reciverBuffer.write(ET.tostring(res))

    def handlePre(self, element: ET.Element):
        if "type" in element.attrib.keys():
            if element.attrib["type"] == "subscribe":
                res = self._PresenceManager.feed(element)
                print(res)

