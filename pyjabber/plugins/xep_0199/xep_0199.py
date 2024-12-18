from xml.etree import ElementTree as ET

from pyjabber.stanzas.IQ import IQ
from pyjabber.utils import Singleton
from pyjabber.metadata import host


class Ping(metaclass=Singleton):
    def feed(self, jid: str, element: ET.Element):
        return ET.tostring(
            IQ(
                type_=IQ.TYPE.RESULT,
                id_=element.attrib.get('id'),
                from_=host.get(),
                to=element.attrib.get('to')
            )
        )
