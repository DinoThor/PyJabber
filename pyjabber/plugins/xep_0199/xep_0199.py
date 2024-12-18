from xml.etree import ElementTree as ET

from pyjabber.stanzas.IQ import IQ
from pyjabber.utils import Singleton
from pyjabber.metadata import host


class Ping(metaclass=Singleton):
    def feed(self, element: ET.Element):
        if element.attrib.get('to') and element.attrib.get('to') == host.get():
            return ET.tostring(
                IQ(
                    type_=IQ.TYPE.RESULT,
                    id_=element.attrib.get('id'),
                    from_=host.get(),
                    to=element.attrib.get('to')
                )
            )
