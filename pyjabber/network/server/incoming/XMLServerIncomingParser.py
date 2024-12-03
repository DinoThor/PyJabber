from enum import Enum
from loguru import logger
from xml.etree import ElementTree as ET

from pyjabber.network.XMLParser import XMLParser
from pyjabber.stream import Stream
from pyjabber.stream.StreamHandler import Signal
from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler
from pyjabber.utils import ClarkNotation as CN


class StreamState(Enum):
    """
    Stream connection states.
    """
    CONNECTED = 0
    READY = 1


class XMLServerIncomingParser(XMLParser):
    """
    Manages the stream data and process the XML objects.
    Inheriting from sax.ContentHandler
    """
    def __init__(self, host, buffer, starttls):
        super().__init__(host, buffer, starttls)
        self._streamHandler = StreamServerIncomingHandler(host, buffer, starttls)

    def startElementNS(self, name, qname, attrs):
        logger.debug(f"Start element NS: {name}")

        if self._stack:  # "<stream:stream>" tag already present in the data stack
            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
            )
            self._stack.append(elem)

        elif name[1] == "stream" and name[0] == "http://etherx.jabber.org/streams":
            self._buffer.write(Stream.responseStream(attrs))

            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
            )

            self._stack.append(elem)
            self._streamHandler.handle_open_stream()

        else:
            raise Exception()

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
            if self._state == StreamState.READY:  # Ready to process stanzas
                self._stanzaHandler.feed(elem)
            else:
                signal = self._streamHandler.handle_open_stream(elem)
                if signal == Signal.RESET and "stream" in self._stack[-1].tag:
                    self._stack.clear()
                elif signal == Signal.DONE:
                    self._stanzaHandler = StanzaServerIncomingHandler(self._buffer)
                    self._state = StreamState.READY
