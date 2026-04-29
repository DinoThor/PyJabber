import asyncio
from asyncio import Transport
from xml.etree import ElementTree as ET
from xml.sax import ContentHandler

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.handlers.StanzaHandler import StanzaHandler
from pyjabber.stream.negotiators.StreamNegotiator import StreamNegotiator
from pyjabber.stream.QueueBridge import QueueBridge
from pyjabber.utils import ClarkNotation as CN


class XMLParser(ContentHandler):
    """
    Manages the stream data and process the XML objects.
    Inheriting from sax.ContentHandler

    :param transport: Transport instance of the connected client. Used to send replays
    """

    __slots__ = ()

    def __init__(
        self,
        transport,
        protocol,
        stream_negotiator=StreamNegotiator,
        stanza_handler=StanzaHandler,
    ):
        super().__init__()
        self._stack = []

        self._transport = transport
        self._protocol = protocol
        self._stream_negotiator = QueueBridge(
            transport, protocol, self, stream_negotiator, stanza_handler
        )

        self._connection_manager = ConnectionManager()
        self._peer = transport.get_extra_info("peername")

        self._queue_bridge_task = asyncio.create_task(self._stream_negotiator.feed())

    @property
    def transport(self) -> Transport:
        return self._transport

    @transport.setter
    def transport(self, transport: Transport):
        self._transport = transport

    def startElementNS(self, name, qname, attrs):
        if self._stack:  # "<stream:stream>" tag already present in the data stack
            elem = ET.Element(
                CN.clark_from_tuple(name),
                attrib={
                    CN.clark_from_tuple(key): item for key, item in dict(attrs).items()
                },
            )
            self._stack.append(elem)

        elif name[1] == "stream" and name[0] == "http://etherx.jabber.org/streams":
            elem = ET.Element(
                CN.clark_from_tuple(name),
                attrib={
                    CN.clark_from_tuple(key): item for key, item in dict(attrs).items()
                },
            )
            self._stack.append(elem)

            self._stream_negotiator.put(elem)

        else:
            raise Exception()

    def endElementNS(self, name, qname):
        if "stream" in name:
            self._connection_manager.close(self._peer)
            self._stack.clear()
            return

        if not self._stack:
            raise Exception()

        elem = self._stack.pop()

        if elem.tag != CN.clark_from_tuple(name):
            # INVALID STANZA/MESSAGE
            raise Exception()

        if self._stack[-1].tag != "{http://etherx.jabber.org/streams}stream":
            self._stack[-1].append(elem)

        else:
            self._stream_negotiator.put(elem)

    def characters(self, content: str) -> None:
        if not self._stack:
            raise Exception()

        elem = self._stack[-1]
        if len(elem) != 0:
            child = elem[-1]
            child.tail = (child.tail or "") + content

        else:
            elem.text = (elem.text or "") + content

    def reset_stack(self) -> None:
        self._stack.clear()

    def cancel_queue_bridge(self):
        self._queue_bridge_task.cancel()
