from loguru import logger

class TransportProxy:
    __slots__ = ('_transport', '_peer', '_server')

    def __init__(self, transport, peer, server = False):
        self._transport = transport
        self._peer = peer
        self._server = server

    @property
    def originalTransport(self):
        return self._transport

    def write(self, data):
        logger.trace(f"Sending to {'server ' if self._server else ''}{self._peer}: {data}")
        return self._transport.write(data)

    def __getattr__(self, name):
        return getattr(self._transport, name)
