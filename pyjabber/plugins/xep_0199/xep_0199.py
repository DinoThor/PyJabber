from xml.etree import ElementTree as ET

from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.plugins.PluginInterface import Plugin


class Ping(Plugin):
    def __init__(self) -> None:
        self._connections = ConectionsManager()

    def feed(self, jid: str, element: ET.Element):
        if "to" in element.attrib and element.attrib["to"] == "localhost":
            res = ET.tostring(
                    ET.Element(
                        "iq",
                        attrib={
                            "from"  : "localhost",
                            "id"    : element.attrib["id"],
                            "to"    : element.attrib["to"],
                            "type"  : "result",
                        },
                    )
                )
            
            return [res]
