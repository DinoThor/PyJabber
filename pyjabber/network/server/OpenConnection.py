import asyncio

from pyjabber.network.server.XMLServerProtocol import XMLServerProtocol


def open_server_connection(jid):
    loop = asyncio.get_running_loop()
    loop.run_until_complete(loop.create_task(asyncio_connection(loop, jid)))


async def asyncio_connection(loop: asyncio.AbstractEventLoop, jid):
    return await loop.create_connection(
        lambda: XMLServerProtocol(
            jid=jid,
            namespace="jabber:server",
            connection_timeout=60
        ),
        host=jid,
        port=5269
    )
