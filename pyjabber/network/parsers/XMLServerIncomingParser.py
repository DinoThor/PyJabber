from xml.etree import ElementTree as ET

from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.stream.Stream import Stream
from pyjabber.utils import ClarkNotation as CN
from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler


class XMLServerIncomingParser(XMLParser):
    """
    Manages the stream data and process the XML objects.
    Inheriting from sax.ContentHandler
    """
    stanza_handler_constructor = StanzaServerIncomingHandler
    stream_handler_constructor = StreamServerIncomingHandler
    server: bool = False

    def __init__(self, transport, starttls):
        super().__init__(transport, starttls)
