import asyncio
import pytest
import ssl
from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError
from unittest.mock import patch
from xml.etree import ElementTree as ET

from pyjabber.server import Server
from pyjabber.server_parameters import Parameters
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
        self.send_presence()
        self.get_roster()

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
            self.add_event_handler("session_start", self.session_start)

        def session_start(self, event):
            self.disconnect()

    server = Server(Parameters(database_in_memory=True))
    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    try:
        client = Disconnect(jid="test@localhost", password="1234")
        client.connect()
        await asyncio.wait_for(client.disconnected, 5)

    finally:
        server_task.cancel()
        await server_task


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

    server = Server(Parameters(database_path='./pyjabber.db'))
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
async def test_init_presence():
    class Client(DummyClient):
        def __init__(self, jid, password):
            DummyClient.__init__(self, jid, password)
            self.add_event_handler("session_start", self.session_start)

        def session_start(self, event):
            self.send_presence()
            self.disconnect()

    def reader_interceptor(self, element: ET.Element):
        if element.tag != "presence" or len(element.attrib) > 0:
            pytest.fail()
        StanzaHandler.feed(self, element)

    server = Server(Parameters(database_in_memory=True))
    with patch('pyjabber.stream.StanzaHandler.feed', side_effect=reader_interceptor):
        server_task = asyncio.create_task(server.start())
        await server.ready.wait()

        try:
            client = Client(jid="test@localhost", password="1234")
            client.connect()
            await asyncio.wait_for(client.disconnected, 5)

        finally:
            server_task.cancel()
            await server_task

if __name__ == "__main__":
    pytest.main()

