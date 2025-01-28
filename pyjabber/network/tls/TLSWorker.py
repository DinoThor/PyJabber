import asyncio

from pyjabber.utils import Singleton


class TLSQueue(metaclass=Singleton):
    def __init__(self):
        self.queue = asyncio.Queue()

