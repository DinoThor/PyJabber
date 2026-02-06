from xml.etree import ElementTree as ET

from pyjabber.AppConfig import AppConfig
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID


class Ping:
    @staticmethod
    def feed(jid: JID, element: ET.Element):
        if element.attrib.get('to') == AppConfig.host:
            return ET.tostring(
                IQ(
                    type_=IQ.TYPE.RESULT,
                    id_=element.attrib.get('id'),
                    from_=AppConfig.host,
                    to=str(jid)
                )
            )
