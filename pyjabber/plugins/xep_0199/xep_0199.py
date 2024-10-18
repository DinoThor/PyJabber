from xml.etree import ElementTree as ET

from pyjabber.plugins.PluginInterface import Plugin


class Ping(Plugin):
    def __init__(self, jid: str) -> None:
        self._jid = jid

    def feed(self, element: ET.Element):
        return ET.tostring(
            ET.Element(
                "iq",
                attrib={
                    "from": "localhost",
                    "id": element.attrib.get('id'),
                    "to": element.attrib.get('to'),
                    "type": "result",
                },
            )
        )
