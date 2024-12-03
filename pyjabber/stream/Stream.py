import enum
import xml.etree.ElementTree as ET
from uuid import uuid4


class Namespaces(enum.Enum):
    """
    Defines the available namespaces in the protocol.
    """
    XMLSTREAM = "http://etherx.jabber.org/streams"
    CLIENT = "jabber:client"
    SERVER = "jabber:server"


class Stream(ET.Element):

    class Namespaces(enum.Enum):
        XMLSTREAM = "http://etherx.jabber.org/streams"
        CLIENT = "jabber:client"
        SERVER = "jabber:server"

    def __init__(
            self,
            id=None,
            from_=None,
            to=None,
            version="1.0",
            xml_lang="en",
            xmlns=Namespaces.CLIENT.value):

        if not id:
            id = str(uuid4())

        attrib = {
            k: v for k, v in (
                ("id", id),
                ("from", from_),
                ("to", to),
                ("version", version),
                ("xml:lang", xml_lang),
                ("xmlns", xmlns)) if v is not None
        }

        attrib["xmlns:stream"] = Namespaces.XMLSTREAM.value

        super().__init__("stream:stream", attrib)

    def open_tag(self) -> bytes:
        tag = f'<{self.tag}'
        for a in self.attrib:
            tag += f" {a}='{self.attrib[a]}'"
        tag += '>'
        return tag.encode()


def responseStream(attrs):
    attrs = dict(attrs)

    id = str(uuid4())
    from_ = attrs.pop((None, "from"), None)
    to = attrs.pop((None, "to"), None)
    version = attrs.pop((None, "version"), "1.0")
    lang = attrs.pop(("http://www.w3.org/XML/1998/namespace", "lang"), None)

    stream = Stream(
        id=id,
        from_=to,
        to=from_,
        version=version,
        xml_lang=lang
    )

    return stream.open_tag()
