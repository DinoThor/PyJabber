from asyncio import BaseProtocol
from enum import Enum
from loguru import logger
from xml.sax import ContentHandler
from xml.etree import ElementTree as ET

from pyjabber.stream import Stream
from pyjabber.stream .StreamHandler import StreamHandler, Signal
from pyjabber.stream .StanzaHandler import StanzaHandler
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.utils import ClarkNotation as CN


class StreamState(Enum):
    """
    Stream connection states.
    """
    CONNECTED   = 0
    READY       = 1


class XMPPStreamHandler(ContentHandler):
    """
    Manages the stream data an process the XML objects.
    Inheriting from sax.ContentHandler
    """

    __slots__ = [
        "_state", 
        "_buffer", 
        "_elementStack",
        "_streamHandler",
        "_stanzaHandler"
    ]

    def __init__(self, buffer, starttls):
        super().__init__()
        self._state         = StreamState.CONNECTED
        self._buffer        = buffer
        self._streamHandler = StreamHandler(self._buffer, starttls)
        self._stanzaHandler = None

        self._connectons    = ConectionsManager()

        self._stack         = []

    @property
    def buffer(self) -> BaseProtocol:
        return self._buffer

    @buffer.setter
    def buffer(self, value: BaseProtocol):
        self._buffer                = value
        self._streamHandler.buffer  = value

    def startElementNS(self, name, qname, attrs):
        logger.debug(f"Start element NS: {name}")   

        if self._stack:     # "<stream:stream>" tag already present in the data stack
            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib  = {CN.clarkFromTuple(key):item for key, item in dict(attrs).items()}
            )
            self._stack.append(elem)

        elif name[1] == "stream" and name[0] == "http://etherx.jabber.org/streams":
            # self._buffer.write(b"<?xml version='1.0'?>")
            self._buffer.write(Stream.responseStream(attrs))
            
            elem = ET.Element(
                CN.clarkFromTuple(name),
                attrib  = {CN.clarkFromTuple(key):item for key, item in dict(attrs).items()}
            )

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
            raise Exception() #TODO: INVALID STANZA/MESSAGE

        if "stream" not in self._stack[-1].tag:
            self._stack[-1].append(elem)

        else:
            if self._state == StreamState.READY:    # Ready to process stanzas
                self._stanzaHandler.feed(elem)
            else:
                signal = self._streamHandler.handle_open_stream(elem)
                if signal == Signal.RESET and "stream" in self._stack[-1].tag:
                    self._stack.pop()
                elif signal == Signal.DONE:        
                    self._stanzaHandler = StanzaHandler(self._buffer)
                    self._state = StreamState.READY


    def characters(self, content: str) -> None:
        if not self._stack:
            raise Exception()
        
        elem = self._stack[-1]
        if len(elem) != 0:
            child = elem[-1]
            child.tail = (child.tail or '') + content

        else :
            elem.text = (elem.text or '') + content
