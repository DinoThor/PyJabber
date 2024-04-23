import xml.etree.ElementTree as ET

from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.stanzas.Message import Message

class StanzaHandler():
    def __init__(self, buffer) -> None:
        peername = buffer.get_extra_info('peername')
        
        self._buffer = buffer
        self._connections   = ConectionsManager()
        self._pluginManager = PluginManager(self._connections.get_jid(peername))
        self._functions     = {
            "jabber:client#iq"          : self.handleIQ,
            "jabber:client#message"     : self.handleMsg,
            "jabber:client#presence"    : self.handlePre
        }

    def feed(self, element: ET.Element):
        try:
            self._functions[element.tag](element)
        except KeyError:
            raise Exception()
        
    def handleIQ(self, element: ET.Element):
        res = self._pluginManager.feed(element)
        self._buffer.write(res)


    def handleMsg(self, element: ET.Element):
        reciverBuffer = self._connections.get_buffer_by_jid(element.attrib["to"])
        res = Message(
            mto     = element.attrib["to"],
            mfrom   = element.attrib["from"],
            id      = element.attrib["id"],
            body    = element.find("jabber:client#body").text
        ) 
        reciverBuffer.write(ET.tostring(res))

    def handlePre(self, element: ET.Element):
        pass