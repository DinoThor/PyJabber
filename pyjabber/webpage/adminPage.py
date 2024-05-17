import asyncio
from contextlib import closing
import os
from aiohttp import web
from pyjabber.db.database import connection
import json
from loguru import logger


async def handleUser(request):
    with closing(connection()) as con:
        res = con.execute("SELECT jid FROM credentials")
        res = res.fetchall()

    users = []
    for index, r in enumerate(res):
        users.append(
            {
                "id"    : index,
                "jid"   : r 
            }
        )
    
    return web.Response(text=json.dumps(users))

async def handle(request):
    return web.FileResponse(os.getcwd() + '/pyjabber/webpage/build/index.html')

async def serverInstance():
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/api/users', handleUser)
    app.router.add_static('/static', os.getcwd() + '/pyjabber/webpage/build/static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9090)
    await site.start()

    logger.info("Serving admin webpage on http://localhost:9090")
    while True:
        await asyncio.sleep(3600)  # Keep alive the server
