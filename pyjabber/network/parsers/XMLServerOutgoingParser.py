from loguru import logger
from xml.etree import ElementTree as ET

from pyjabber import metadata
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.stream import Stream
from pyjabber.stream.StanzaHandler import StanzaHandler
from pyjabber.stream.StreamHandler import Signal
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.server.outgoing.StreamServerOutcomingHandler import StreamServerOutcomingHandler
from pyjabber.utils import ClarkNotation as CN


class XMLServerOutgoingParser(XMLParser):
    """
    Manages the stream data and process the XML objects.
    Inheriting from sax.ContentHandler
    """
    stream_handler_constructor = StreamServerOutcomingHandler

    def __init__(self, transport, starttls):
        super().__init__(transport, starttls)
        # self._receiver_host = transport.get_extra_info("")
        self.initial_stream()

    def startElementNS(self, name, qname, attrs):
        CN.clarkFromTuple(name)

        elem = ET.Element(
            CN.clarkFromTuple(name),
            attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
        )
        self._stack.append(elem)

    def endElementNS(self, name, qname):
        if name == "</stream:stream>":
            self._buffer.write(b'</stream:stream>')
            self._stack.clear()
            return

        if not self._stack:
            raise Exception()

        elem = self._stack.pop()

        if elem.tag != CN.clarkFromTuple(name):
            self._buffer.write(SE.not_well_formed())
            self._stack.clear()
            return

        if self._stack[-1].tag != '{http://etherx.jabber.org/streams}stream':
            self._stack[-1].append(elem)

        else:
            if self._state == self.StreamState.READY:  # Ready to process stanzas
                self._stanzaHandler.feed(elem)
            else:
                signal = self._streamHandler.handle_open_stream(elem)
                if signal == Signal.RESET:
                    self._stack.clear()
                    self.initial_stream()
                elif signal == Signal.DONE:
                    self._stanzaHandler = StanzaHandler(self._buffer, None)
                    self._state = self.StreamState.READY

    def initial_stream(self):
        initial_stream = Stream.Stream(
            from_=metadata.HOST,
            to=self._host,
            xmlns=Stream.Namespaces.SERVER.value
        )

        initial_stream = initial_stream.open_tag()
        self._buffer.write(initial_stream)
