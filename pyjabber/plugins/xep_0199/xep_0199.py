from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.utils import Singleton
from pyjabber.metadata import host


class Ping(metaclass=Singleton):
    def feed(self, jid: str, element: ET.Element):
        return ET.tostring(
            ET.Element(
                "iq",
                attrib={
                    "from": host.get(),
                    "id": element.attrib.get('id') or str(uuid4()),
                    "to": element.attrib.get('to'),
                    "type": "result",
                },
            )
        )
