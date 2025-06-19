import asyncio
import pytest
import ssl
from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError
from unittest.mock import patch
from xml.etree import ElementTree as ET

from pyjabber.server import Server
from pyjabber.server_parameters import Parameters
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.stream.StanzaHandler import StanzaHandler


class DummyClient(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("register", self.register)
        self.register_plugin("xep_0077")

    def session_start(self, event):
        pass

    async def register(self, event):
        resp = self.Iq()
        resp["type"] = "set"
        resp["register"]["username"] = self.boundjid.user
        resp["register"]["password"] = self.password

        try:
            await resp.send()
        except IqError:
            pass


@pytest.mark.asyncio
async def test_connection():
    class Disconnect(DummyClient):
        def __init__(self, jid, password):
            DummyClient.__init__(self, jid, password)
            self._session_reached = False

        def session_start(self, event):
            self._session_reached = True
            self.disconnect()

    server = Server(Parameters(database_in_memory=True))
    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    client = Disconnect(jid="test@localhost", password="1234")
    assert client._session_reached is False

    try:
        client.connect()
        await asyncio.wait_for(client.disconnected, 5)
    finally:
        server_task.cancel()
        await server_task

    assert client._session_reached


@pytest.mark.asyncio
async def test_unauthorized():
    class Disconnect(DummyClient):
        def __init__(self, jid, password):
            DummyClient.__init__(self, jid, password)
            self.add_event_handler("session_start", self.session_start)
            self.login_reached = asyncio.Future()

        def session_start(self, event):
            self.login_reached.set_result("REACHED")
            self.disconnect()

    server = Server(Parameters(
        database_path='./pyjabber.db',
        plugins=[
            # 'jabber:iq:register',
            'jabber:x:data',
            'urn:xmpp:ping',
        ]))
    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    try:
        client = Disconnect(jid="test@localhost", password="4321")
        client.connect()
        try:
            await asyncio.wait_for(client.disconnected, 5)
            if client.login_reached.done() and client.login_reached.result() == "REACHED":
                pytest.fail("Client was able to login")
        except asyncio.TimeoutError:
            assert pytest.fail("Server unreachable")

    finally:
        server_task.cancel()
        await server_task


@pytest.mark.asyncio
async def test_roster():
    class Client(DummyClient):
        def __init__(self, jid, password):
            DummyClient.__init__(self, jid, password)
            self.add_event_handler("session_start", self.session_start)
            self.add_event_handler("roster_update", self.roster_updated)

        def session_start(self, event):
            self.get_roster()

        def roster_updated(self, event):
            self.disconnect()

    server = Server(Parameters(database_in_memory=True))
    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    try:
        client = Client(jid="roster_test_1@localhost", password="1234")
        client.connect()
        await asyncio.wait_for(client.disconnected, 5)

    finally:
        server_task.cancel()
        await server_task

    presence = Presence()

    assert 'a' == 21

@pytest.mark.asyncio
async def test_init_presence():
    class Client(DummyClient):
        def __init__(self, jid, password):
            DummyClient.__init__(self, jid, password)
            self.add_event_handler("session_start", self.session_start)

        def session_start(self, event):
            self.send_presence()
            self.disconnect()

    server = Server(Parameters(database_in_memory=True))
    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    try:
        client = Client(jid="test@localhost", password="1234")
        client.connect()
        await asyncio.wait_for(client.disconnected, 5)

    finally:
        server_task.cancel()
        await server_task

    presence = Presence()

    assert 'a' == 21

if __name__ == "__main__":
    pytest.main()

