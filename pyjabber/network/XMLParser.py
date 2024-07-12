from asyncio import BaseProtocol
from enum import Enum
from xml.etree import ElementTree as ET
from xml.sax import ContentHandler

from loguru import logger

from pyjabber.stream import Stream
from pyjabber.stream.StanzaHandler import StanzaHandler
from pyjabber.stream.StreamHandler import Signal, StreamHandler
from pyjabber.utils import ClarkNotation as CN


class XMLParser(ContentHandler):
    """
        Manages the stream data and process the XML objects.
        Inheriting from sax.ContentHandler

        :param host: Host of the running server
        :param buffer: Transport instance of the connected client. Used to send replays
        :param starttls: Coroutine launched when server and client start the connection upgrade process to TLS
        :param connection_manager: Global instance of the Connection Manager class (Singleton)
        :param queue_message: Global instance of Queue Message class (Singleton)
    """

    def __init__(self, host, buffer, starttls, connection_manager, queue_message):
        super().__init__()

        self._host = host
        self._buffer = buffer
        self._connection_manager = connection_manager
        self._queue_message = queue_message

        self._state = self.StreamState.CONNECTED
        self._stanzaHandler = None
        self._stack = []
        self._streamHandler = StreamHandler(
            self._host, self._buffer, starttls, connection_manager)

    class StreamState(Enum):
        """
        Stream connection states.
        """
        CONNECTED = 0
        READY = 1

    @property
    def buffer(self) -> BaseProtocol:
        return self._buffer

    @buffer.setter
    def buffer(self, value: BaseProtocol):
        self._buffer = value
        self._streamHandler.buffer = value

    def startElementNS(self, name, qname, attrs):
        logger.debug(f"Start element from <{hex(id(self._buffer))}>: {name}")

        if self._stack:  # "<stream:stream>" tag already present in the data stack
            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib={
                    CN.clarkFromTuple(key): item for key,
                    item in dict(attrs).items()})
            self._stack.append(elem)

        elif name[1] == "stream" and name[0] == "http://etherx.jabber.org/streams":
            self._buffer.write(Stream.responseStream(attrs))

            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib={
                    CN.clarkFromTuple(key): item for key,
                    item in dict(attrs).items()})

            self._stack.append(elem)
            self._streamHandler.handle_open_stream()

        else:
            raise Exception()

    def endElementNS(self, name, qname):
        logger.debug(f"End element NS: {qname} : {name}")

        if "stream" in name:
            self._buffer.write(b'</stream:stream>')
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
                if signal == Signal.RESET and "stream" in self._stack[-1].tag:
                    self._stack.clear()
                elif signal == Signal.DONE:
                    self._stanzaHandler = StanzaHandler(
                        self._host, self._buffer, self._connection_manager, self._queue_message)
                    self._state = self.StreamState.READY

    def characters(self, content: str) -> None:
        if not self._stack:
            raise Exception()

        elem = self._stack[-1]
        if len(elem) != 0:
            child = elem[-1]
            child.tail = (child.tail or '') + content

        else:
            elem.text = (elem.text or '') + content
