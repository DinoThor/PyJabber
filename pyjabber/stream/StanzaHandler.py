import xml.etree.ElementTree as ET

from network.ConnectionsManager import ConectionsManager
from stanzas.Message import Message

class StanzaHandler():
    def __init__(self, buffer) -> None:
        self._buffer = buffer

        self._connections   = ConectionsManager()
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
        type = element.attrib["type"]
        
        hand = {
            "get": 2,
            "result" : 2,
            "set": 2,
            "error": 2
        }


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