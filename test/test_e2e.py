import asyncio
import threading

import pytest
import pytest_asyncio
from slixmpp import ClientXMPP

from pyjabber.server import Server


@pytest.mark.asyncio
async def test_client_connection(dummy_client):
    jid, client = dummy_client
    server = Server()

    def init_thread(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=init_thread, args=(thread_loop,))
    thread.start()

    server_task = asyncio.create_task(server.start())
    await server.ready.wait()

    client_future = asyncio.run_coroutine_threadsafe(client.connect(), thread_loop)

    await client.disconnected
    await asyncio.sleep(5)
    await server.stop_server()

if __name__ == "__main__":
    pytest.main()

