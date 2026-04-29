import asyncio
from asyncio import Protocol, Transport
from xml.etree import ElementTree as ET

from pyjabber.stream.utils.Enums import Signal


class QueueBridge:
    __slots__ = (
        "_stream_ready",
        "_transport",
        "_protocol",
        "_parser",
        "_queue",
        "_stream_handler",
        "_stanza_handler",
        "_stanza_handler_class",
    )

    def __init__(self, transport, protocol, parser, stream_handler, stanza_handler):
        self._stream_ready = False

        self._transport: Transport = transport
        self._protocol: Protocol = protocol
        self._parser = parser

        self._queue = asyncio.Queue()

        self._stream_handler = stream_handler(transport, protocol, parser, self)

        self._stanza_handler_class = stanza_handler
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
                    if res == Signal.RESET:
                        self._parser.reset_stack()
                    if res == Signal.DONE:
                        self._stanza_handler = self._stanza_handler_class(
                            self._transport
                        )
                        self._stream_handler = None
                        self._stream_ready = True

        except asyncio.CancelledError:
            self._transport = None
            self._protocol = None
            self._parser = None
            self._stream_handler = None
            self._stanza_handler = None
