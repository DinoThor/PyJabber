import asyncio
from collections import deque

from pyjabber.network.ConnectionManager import ConnectionManager


class QueueMessage:
    def __init__(self, connection_manager):
        self._queue = []
        self._loop = asyncio.get_event_loop()
        self._chrono_task = asyncio.Event()

        self._connection_manager: ConnectionManager = connection_manager

    def enqueue(self, host, element):
        self._queue.append((host, element))
        self._loop.create_task(self.chrono())

    async def chrono(self):
        while len(self._queue) > 0:
            await asyncio.sleep(1)
            for host, element in self._queue:
                buffer = self._connection_manager.get_server_buffer(host)
                if buffer:
                    buffer[-1].write(element)
                    self._queue.remove((host, element))
