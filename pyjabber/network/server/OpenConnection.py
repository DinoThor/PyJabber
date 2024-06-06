import asyncio

from pyjabber.network.server.XMLServerProtocol import XMLServerProtocol 


def open_server_connection(jid):
    loop = asyncio.get_running_loop()
    print(loop)
    # task = loop.create_task(asyncio_connection(loop, jid))
    loop.run_until_complete(loop.create_task(asyncio_connection(loop, jid)))
    

    # try:
    #     loop.run_until_complete(loop.create_task(asyncio_connection(loop, jid)))
    #     loop.run_forever()
    # except:
    #     pass
    # finally:
    #     tasks = asyncio.all_tasks(loop)
    #     print(tasks)
    #     for task in tasks:
    #         task.cancel()
    #     loop.run_until_complete(asyncio.gather(*tasks, return_exceptions = True))
    #     loop.close()

async def asyncio_connection(loop: asyncio.AbstractEventLoop, jid):
    return await loop.create_connection(
       lambda: XMLServerProtocol(
           namespace= "jabber:server",
           connection_timeout=60
       ),
       host=jid,
       port=5269
    )
