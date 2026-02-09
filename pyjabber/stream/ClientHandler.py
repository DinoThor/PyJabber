import asyncio
from xml.etree import ElementTree as ET

from pyjabber.stream.StanzaHandler import StanzaHandler
from pyjabber.stream.StreamHandler import StreamHandler
from pyjabber.stream.utils.Enums import Signal


class ClientHandle:
    def __init__(self, transport, protocol, parser):
        self._stream_ready = False

        self._transport = transport
        self._protocol = protocol
        self._parser = parser

        self._queue = asyncio.Queue()

        self._stream_handler = StreamHandler(transport, protocol, parser, self)
        self._stanza_handler = None

    def put(self, element: ET.Element):
        self._queue.put_nowait(element)

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, transport):
        self._transport = transport

    async def feed(self):
        try:
            while True:
                element = await self._queue.get()

                if self._stream_ready:
                    await self._stanza_handler.feed(element)

                else:
                    res = await self._stream_handler.handle_open_stream(element)
                    if res == Signal.DONE:
                        self._stanza_handler = None
                        self._stream_ready = True

        except asyncio.CancelledError:
            pass
