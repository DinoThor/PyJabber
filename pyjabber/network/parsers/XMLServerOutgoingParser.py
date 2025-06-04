import asyncio
from xml.etree import ElementTree as ET

from pyjabber import metadata
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.stream import Stream
from pyjabber.stream.StreamHandler import Signal
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.server.outgoing.StreamServerOutgoingHandler import StreamServerOutgoingHandler
from pyjabber.utils import ClarkNotation as CN


class XMLServerOutgoingParser(XMLParser):
    stream_handler_constructor = StreamServerOutgoingHandler

    def __init__(self, remote_host, transport, starttls):
        super().__init__(transport, starttls)
        self._connection_queue: asyncio.Queue = metadata.CONNECTION_QUEUE
        self._remote_host = remote_host

        self.initial_stream()

    def startElementNS(self, name, qname, attrs):
        elem = ET.Element(
            CN.clarkFromTuple(name),
            attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
        )

        self._stack.append(elem)

    def endElementNS(self, name, qname):
        if name == "</stream:stream>":
            self._transport.write(b'</stream:stream>')
            self._stack.clear()
            return

        if not self._stack:
            raise Exception()

        elem = self._stack.pop()

        if elem.tag != CN.clarkFromTuple(name):
            self._transport.write(SE.not_well_formed())
            self._stack.clear()
            return

        if self._stack[-1].tag != '{http://etherx.jabber.org/streams}stream':
            self._stack[-1].append(elem)

        else:
            if self._state == self.StreamState.READY:  # Ready to process stanzas
                self._stanzaHandler.feed(elem)
            else:
                signal = self._streamHandler.handle_open_stream(elem)
                if signal == Signal.CLEAR:
                    self._stack.clear()
                elif signal == Signal.RESET:
                    self._stack.clear()
                    self.initial_stream()
                elif signal == Signal.DONE:
                    self._state = self.StreamState.READY
                    self._connection_queue.put_nowait(('CONNECTION', self._remote_host))

    def initial_stream(self):
        initial_stream = Stream.Stream(
            from_=metadata.HOST,
            to=self._remote_host,
            xmlns=Stream.Namespaces.SERVER.value
        )

        initial_stream = initial_stream.open_tag()
        self._transport.write(initial_stream)
