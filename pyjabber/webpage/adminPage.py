import asyncio
import os

from aiohttp import web
from loguru import logger
from pyjabber.webpage.api import api 


async def serverInstance():
    app = web.Application()
    app.router.add_get('/', api.handle)
    app.router.add_get('/api/users', api.handleUser)
    app.router.add_post('/api/createuser', api.handleRegister)
    app.router.add_delete('/api/users/{id}', api.handleDelete)
    app.router.add_static('/static', os.getcwd() + '/pyjabber/webpage/build/static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9090)
    await site.start()

    logger.info("Serving admin webpage on http://localhost:9090")
    while True:
        await asyncio.sleep(3600)  # Keep alive the server
