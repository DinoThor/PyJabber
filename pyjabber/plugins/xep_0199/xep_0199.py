from xml.etree import ElementTree as ET

from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber import metadata


class Ping:
    @staticmethod
    def feed(jid: JID, element: ET.Element):
        if element.attrib.get('to') == metadata.HOST:
            return ET.tostring(
                IQ(
                    type_=IQ.TYPE.RESULT,
                    id_=element.attrib.get('id'),
                    from_=metadata.HOST,
                    to=str(jid)
                )
            )
