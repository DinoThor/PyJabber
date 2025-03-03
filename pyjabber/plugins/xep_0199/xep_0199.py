from xml.etree import ElementTree as ET

from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton
from pyjabber.metadata import host


class Ping(metaclass=Singleton):
    def feed(self, jid: JID, element: ET.Element):
        if element.attrib.get('to') == host.get():
            return ET.tostring(
                IQ(
                    type_=IQ.TYPE.RESULT,
                    id_=element.attrib.get('id'),
                    from_=host.get(),
                    to=str(jid)
                )
            )
