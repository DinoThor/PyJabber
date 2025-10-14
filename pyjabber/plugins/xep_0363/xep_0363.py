import xml.etree.ElementTree as ET

from pyjabber import metadata
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton
from pyjabber.stanzas.error import StanzaError as SE

class HTTPFieldUpload(metaclass=Singleton):
    __slots__ = ('_handlers', '_max_size')

    def __init__(self):
        self._max_size = metadata.ITEMS["upload.$"]["extra"]["max-size"]

    def feed(self, jid: JID, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        request = element.find('{urn:xmpp:http:upload:0}request')
        if request is None:
            return SE.invalid_xml()

        filename = request.attrib["filename"]
        size = request.attrib["size"]
        content_type = request.attrib["content"]

        if size > self._max_size:
            return SE.not_acceptable(f"File too large. The maximum file size is {self._max_size} bytes")

        return None

