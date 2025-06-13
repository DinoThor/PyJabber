from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler


class XMLServerIncomingParser(XMLParser):
    stanza_handler_constructor = StanzaServerIncomingHandler
    stream_handler_constructor = StreamServerIncomingHandler
    server: bool = False

    def __init__(self, transport, starttls):
        super().__init__(transport, starttls)
