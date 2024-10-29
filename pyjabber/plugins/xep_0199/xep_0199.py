from xml.etree import ElementTree as ET

from pyjabber.utils import Singleton


class Ping(metaclass=Singleton):
    def feed(self, jid: str, element: ET.Element):
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
