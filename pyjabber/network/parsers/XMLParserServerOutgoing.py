import asyncio
from xml.etree import ElementTree as ET

from pyjabber import AppConfig
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.stream.handlers.ServerStanzaHandler import ServerStanzaHandler
from pyjabber.stream.negotiators.ServerStreamNegotiator import StreamServerNegotiator
from pyjabber.stream.utils import Stream
from pyjabber.utils import ClarkNotation as CN


class XMLParserServerOutgoing(XMLParser):
    def __init__(self, transport, protocol, host):
        super().__init__(
            transport, protocol, StreamServerNegotiator, ServerStanzaHandler
        )
        self._connection_queue: asyncio.Queue = get_queue(QueueName.CONNECTIONS)
        self._host = host

        self._initial_stream()

    def startElementNS(self, name, qname, attrs):
        elem = ET.Element(
            CN.clark_from_tuple(name),
            attrib={
                CN.clark_from_tuple(key): item for key, item in dict(attrs).items()
            },
        )

        self._stack.append(elem)

    def reset_stack(self) -> None:
        super().reset_stack()
        self._initial_stream()

    def _initial_stream(self):
        initial_stream = Stream.Stream(
            from_=AppConfig.app_config.host,
            to=self._host,
            xmlns=Stream.Namespaces.SERVER.value,
        )

        initial_stream = initial_stream.open_tag()
        self._transport.write(initial_stream)
