import asyncio
from loguru import logger

from pyjabber.utils import Singleton


class QueueMessage(metaclass=Singleton):
    def __init__(self, connection_manager=None):
        self._queue = []
        self._loop = asyncio.get_event_loop()
        self._chrono_task = asyncio.Event()

        if connection_manager:
            self._connection_manager = connection_manager

    def enqueue(self, host, element):
        self._queue.append((host, element))
        self._loop.create_task(self.chrono())

    async def chrono(self):
        while len(self._queue) > 0:
            await asyncio.sleep(5)
            for host, element in self._queue:
                buffer = self._connection_manager.get_server_buffer(host)
                if buffer:
                    buffer[-1].write(element)
                    logger.debug(f"Routed message to {host}")
                    self._queue.remove((host, element))
