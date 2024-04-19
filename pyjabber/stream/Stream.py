import enum
from uuid import uuid4
import xml.etree.ElementTree as ET
from slixmpp.xmlstream import tostring

class Namespaces(enum.Enum):
    '''
    Defines the available namespaces in the protocol.
    '''
    XMLSTREAM = "http://etherx.jabber.org/streams"
    CLIENT = "jabber:client"
    SERVER = "jabber:server"


    
    # def open_tag(self):
    #     '''
    #     Return the open tag of the element.
    #     '''
    #     tag = '<' + self.tag + ' '
    #     for a in self.attrib:
    #         tag += a + '="' + self.attrib[a] + '" '
    #     tag += '>'
    #     return tag.encode()

        

class Stream(ET.Element):
    '''
    Stream open tag to open a stream connection.
    '''
    def __init__(
            self, 
            id_         = None, 
            from_       = None, 
            to          = None, 
            version     = "1.0", 
            xml_lang    = "en", 
            xmlns       = Namespaces.CLIENT.value):
        
        attrib = {
            k: v for k, v in (
                ("id", id_), 
                ("from", from_), 
                ("to", to), 
                ("version", version), 
                ("xml:lang", xml_lang), 
                ("xmlns", xmlns)) if v is not None
        }

        super().__init__("stream:stream", attrib)


def responseStream(attrs):
    # Load attributes
    attrs = dict(attrs)

    # Get attributes
    id_     = str(uuid4())
    from_   = attrs.pop((None, "from"), None)
    to      = attrs.pop((None, "to"), None)
    version = attrs.pop((None, "version"), "1.0")
    lang    = attrs.pop(("http://www.w3.org/XML/1998/namespace", "lang"), None)

    # Create response attributes
    stream = Stream(
        id_         = id_,
        from_       = to,
        to          = from_,
        version     = version,
        xml_lang    = lang
    )

    return tostring(stream, open_only = True).encode(encoding='utf-8')

def recivedStream(attrs):
    attrs = dict(attrs)

    from_   = attrs.pop((None, "from"), None)
    to      = attrs.pop((None, "to"), None)
    version = tuple(map(int, attrs.pop((None, "version"), "0.9").split(".")))
    lang    = attrs.pop(("http://www.w3.org/XML/1998/namespace", "lang"), None)

    return Stream(
        from_       = from_,
        to          = to,
        version     = version,
        xml_lang    = lang,
        xmlns       = "jabber:client"
    )
