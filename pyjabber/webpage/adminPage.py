import asyncio
import os

from aiohttp import web
from loguru import logger
from pyjabber.webpage.api import api

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


async def admin_instance():
    app = web.Application()
    app.router.add_get('/', getIndex)
    app.router.add_get('/api/users', api.handleUser)
    app.router.add_get('/api/roster/{id}', api.handleRoster)
    app.router.add_post('/api/createuser', api.handleRegister)
    app.router.add_delete('/api/users/{id}', api.handleDelete)
    app.router.add_static('/static', FILE_PATH + '/build/static')
    app.router.add_static('/', FILE_PATH + '/build/')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9090)
    await site.start()

    logger.info("Serving admin webpage on http://localhost:9090")
    while True:
        await asyncio.sleep(3600)  # Keep alive the server


async def getIndex(request):
    return web.FileResponse(FILE_PATH + '/build/index.html')
