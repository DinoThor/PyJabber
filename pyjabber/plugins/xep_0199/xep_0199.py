from xml.etree import ElementTree as ET

from pyjabber import AppConfig
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID


class Ping:
    @staticmethod
    async def feed(jid: JID, element: ET.Element):
        if element.attrib.get("to") == AppConfig.app_config.host:
            return ET.tostring(
                IQ(
                    type_=IQ.TYPE.RESULT,
                    id_=element.attrib.get("id"),
                    from_=AppConfig.app_config.host,
                    to=str(jid),
                )
            )
