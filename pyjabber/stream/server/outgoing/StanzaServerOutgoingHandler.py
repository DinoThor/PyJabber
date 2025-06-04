import asyncio
import xml.etree.ElementTree as ET

from pyjabber import metadata
from pyjabber.network.ConnectionManager import ConnectionManager


class StanzaServerOutgoingHandler:
    def __init__(self, buffer, host) -> None:
        self._buffer = buffer
        self._remote_host = host
        self._connections = ConnectionManager()

        self._message_queue = metadata.MESSAGE_QUEUE
        self._message_persistence = metadata.MESSAGE_PERSISTENCE
        # self._connection_queue: asyncio.Queue = metadata.CONNECTION_QUEUE

        # self._connection_queue.put_nowait(('CONNECTION', self._remote_host))

    def feed(self, element: ET.Element):
        pass
