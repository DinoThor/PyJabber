from loguru import logger
from xml.etree import ElementTree as ET

from pyjabber.network.XMLParser import XMLParser
from pyjabber.stream import Stream
from pyjabber.stream.StanzaHandler import StanzaHandler
from pyjabber.stream.StreamHandler import Signal
from pyjabber.stream.server.outcoming.StreamServerOutcomingHandler import StreamServerOutcomingHandler
from pyjabber.utils import ClarkNotation as CN


class XMLServerOutcomingParser(XMLParser):
    """
    Manages the stream data and process the XML objects.
    Inheriting from sax.ContentHandler
    """

    def __init__(self, buffer, starttls, connection_manager, queue_message, host, my_host):
        super().__init__(buffer, starttls, connection_manager, queue_message)
        self._host = host
        self._my_host = my_host
        self._streamHandler = StreamServerOutcomingHandler(self._buffer, starttls, connection_manager, my_host)
        self.initial_stream()

    def startElementNS(self, name, qname, attrs):
        logger.debug(f"Start element NS: {name}")

        clark = CN.clarkFromTuple(name)
        if CN.clarkFromTuple(name) == '{http://etherx.jabber.org/streams}stream' and self._stack:
            # ERROR Stream already present in stack
            raise Exception()

        elem = ET.Element(
            CN.clarkFromTuple(name),
            attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
        )
        self._stack.append(elem)

    def endElementNS(self, name, qname):
        logger.debug(f"End element NS: {qname} : {name}")

        if name == "</stream:stream>":
            self._buffer.write(b'</stream>')
            self._stack.clear()
            return

        if not self._stack:
            raise Exception()

        elem = self._stack.pop()

        if elem.tag != CN.clarkFromTuple(name):
            # INVALID STANZA/MESSAGE
            raise Exception()

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
                    self._stanzaHandler = StanzaHandler(self._buffer, self._connection_manager, None)
                    self._state = self.StreamState.READY

    def initial_stream(self):
        initial_stream = Stream.Stream(
            from_=self._my_host,
            to=self._host,
            xmlns=Stream.Namespaces.SERVER.value
        )

        initial_stream = initial_stream.open_tag()
        self._buffer.write(initial_stream)
