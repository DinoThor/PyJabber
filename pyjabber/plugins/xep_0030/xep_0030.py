from xml.etree import ElementTree as ET

from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.stanzas.error import StanzaError as SE


class Disco(Plugin):
    def __init__(self):
        self._handlers = {
            "get": self.handle_get
        }

    def feed(self, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        return self._handlers[element.attrib["type"]](element)


    def handle_get(self, element: ET.Element):
        element.find('')
