import asyncio

import pytest
import pytest_asyncio
from slixmpp import ClientXMPP

from pyjabber.server import Server

@pytest.mark.asyncio
async def test_client_connection(dummy_client):
    jid, client = dummy_client
    server = Server()

    asyncio.create_task(server.start())
    await server.ready.wait()

    client.connect()
    await asyncio.sleep(5)
    await server.stop_server()

if __name__ == "__main__":
    pytest.main()

