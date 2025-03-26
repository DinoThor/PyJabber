import asyncio
import os

from aiohttp import web
from loguru import logger

from pyjabber.webpage.api import api

FILE_PATH = os.path.dirname(os.path.abspath(__file__))

class AdminPage:
    def __init__(self):
        self._app = web.Application()
        self._app.router.add_get('/', self.getIndex)
        self._app.router.add_get('/api/users', api.handleUser)
        self._app.router.add_get('/api/roster/{id}', api.handleRoster)
        self._app.router.add_post('/api/createuser', api.handleRegister)
        self._app.router.add_delete('/api/users/{id}', api.handleDelete)
        self._app.router.add_static('/static', FILE_PATH + '/build/static')
        self._app.router.add_static('/', FILE_PATH + '/build/')

    @property
    def app(self):
        return self._app

    async def getIndex(self, request):
        return web.FileResponse(FILE_PATH + '/build/index.html')

    async def start(self):
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 9090)
        try:
            await site.start()
        except OSError as e:
            logger.error(e)
            return

        logger.info("Serving admin webpage on http://localhost:9090")
        try:
            while True:
                await asyncio.sleep(3600)  # Keep alive the server
        except asyncio.CancelledError:
            await runner.cleanup()

