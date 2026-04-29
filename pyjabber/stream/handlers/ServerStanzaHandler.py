import asyncio
import xml.etree.ElementTree as ET
from asyncio import Transport

from pyjabber import AppConfig
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue


class ServerStanzaHandler:
    def __init__(self, transport: Transport) -> None:
        self._ip = AppConfig.app_config.ip
        self._transport = transport
        self._peername = transport.get_extra_info("peername")

        self._connections = ConnectionManager()

        self._host = self._connections.get_host(self._peername)

        self._presenceManager = Presence()

        self._message_queue = get_queue(QueueName.MESSAGES)
        self._connection_queue: asyncio.Queue = get_queue(QueueName.CONNECTIONS)

        self._message_persistence = AppConfig.app_config.message_persistence

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre,
        }

        get_queue(QueueName.CONNECTIONS).put_nowait(
            NewConnectionWrapper(self._host, False)
        )

    async def feed(self, element: ET.Element):
        pass

    async def handle_iq(self, element: ET.Element):
        pass

    async def handle_msg(self, element: ET.Element):
        pass

    async def handle_pre(self, element: ET.Element):
        pass
