import asyncio
import os
from aiohttp import web
import aiohttp
# from pyjabber.db.database import connection
import json
import aiohttp_cors
import logging
import yarl



async def handleUser(request):
    data = {
        "users": [
            {"id": 1, "jid": "demo", "hash": 132131},
            {"id": 2, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 1, "jid": "demo", "hash": 132131},
            {"id": 2, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131}
        ]
    }
    data = json.dumps(data)
    return web.Response(text=data)
# app = web.Application()
# app.router.add_static('/static/',
#                           path=os.getcwd() + "/pyjabber/webpage/build/",
#                           show_index=True
#                           )

# app.add_routes([web.static('/', os.getcwd() + "/pyjabber/webpage/build",  follow_symlinks=True)])

# app.add_routes([web.get('/', htmlPage),
#                 web.get('/static/css/main.985302ea.cs', cssPage)])


async def serverInstance():
    logging.getLogger('aiohttp.server')
    logging.basicConfig(level=logging.DEBUG)
    # app = web.Application()
    # app.add_routes([web.static('/prefix/', os.getcwd() + "/pyjabber/webpage/build/", name="prefix")])

    # runner = web.AppRunner(app)
    # await runner.setup()
    # site = web.TCPSite(runner, host='localhost', port=9090)
    # await site.start()

    app = web.Application()
    app.add_routes([web.static('/prefix/', "/home/aaron/Escritorio/build", name="prefix")])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("======= Serving on http://localhost:8080/ =======")
    while True:
        await asyncio.sleep(3600)  # Mantiene el servidor en funcionamiento

async def other_task():
    while True:
        print("Running other task...")
        await asyncio.sleep(5)


async def main():
    await asyncio.gather(
        serverInstance(),
        other_task()
    )


    # app = web.Application()
    # app.add_routes([web.static('/prefix/', os.getcwd() + "/pyjabber/webpage/build/", name="prefix")])
    # await web.run_app(app)

if __name__ == "__main__":
    # serverInstance()
    asyncio.run(main())
