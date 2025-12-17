import asyncio

from pyjabber.stream.StreamHandler import StreamHandler, Signal
from xml.etree import ElementTree as ET

class ClientHandle:
    def __init__(self, transport, protocol, parser):
        self._stream_ready = False

        self._transport = transport
        self._protocol = protocol
        self._parser = parser

        self._queue = asyncio.Queue()

        self._stream_handler = StreamHandler(transport, protocol, parser)

    def put(self, element: ET.Element):
        self._queue.put_nowait(element)

    async def feed(self):
        while True:
            element = await self._queue.get()

            if not self._stream_ready:
                res = await self._stream_handler.handle_open_stream(element)
                if isinstance(res, Signal):
                    pass
