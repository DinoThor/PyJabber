import os

from asyncio import Queue, sleep, create_task
from aiohttp import web
from loguru import logger

from pyjabber.webpage.api import api

class AdminPage:
    def __init__(self):
        self._file_path = os.path.dirname(os.path.abspath(__file__))
        # HTTP
        self._app = web.Application()
        self._app.router.add_get('/', self.getIndex)
        self._app.router.add_get('/api/users', api.handleUser)
        self._app.router.add_get('/api/roster/{id}', api.handleRoster)
        self._app.router.add_post('/api/createuser', api.handleRegister)
        self._app.router.add_delete('/api/users/{id}', api.handleDelete)
        self._app.router.add_static('/static', self._file_path + '/build/static')
        self._app.router.add_static('/', self._file_path + '/build/')

        # WEBSOCKET
        self.log_queue = None
        self._app.router.add_get('/ws', self.websocket_handler)
        self._socket_clients = []

    @property
    def app(self):
        return self._app

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._socket_clients.append(ws)

        logger.info("Client connected to logger socket")
        try:
            async for _ in ws:
                pass
        finally:
            self._socket_clients.remove(ws)
            logger.info("Client disconnected from logger socket")

        return ws

    async def enqueue_log(self, log):
        await self.log_queue.put(log)

    async def broadcast_logs(self):
        while True:
            log = await self.log_queue.get()
            await self.send_log(log)

    async def send_log(self, log):
        for c in self._socket_clients:
            if not c.closed:
                await c.send_json({"log": log})

    async def getIndex(self, request):
        return web.FileResponse(self._file_path + '/build/index.html')

    async def start(self):
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 9090)
        await site.start()

        self.log_queue = Queue()
        create_task(self.broadcast_logs())

        logger.info("Serving admin webpage on http://localhost:9090")
        while True:
            await sleep(3600)  # Keep alive the server

