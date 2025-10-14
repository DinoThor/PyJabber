import asyncio
import os
from typing import List

from aiohttp import web
from aiohttp.web_app import Application
from loguru import logger

from pyjabber import metadata
from pyjabber.webpage.adminPage import get_index, get_static

FILE_PATH = os.path.dirname(os.path.abspath(__file__))

class HttpServer:
    def __init__(self, app_list: List[tuple[str, Application]]):
        self._mainApp = web.Application()
        self._mainApp.router.add_get('/', get_index)
        self._mainApp.router.add_static('/static', get_static())
        for app in app_list:
            self._mainApp.add_subapp(app[0], app[1])


    @property
    def app(self):
        return self._mainApp

    async def start(self):
        runner = web.AppRunner(self._mainApp)
        await runner.setup()
        site = web.TCPSite(runner, metadata.HOST, 9090)
        try:
            await site.start()
        except OSError as e:
            logger.error(e)
            return

        logger.info(f"Serving admin webpage on http://{metadata.HOST}:9090")
        try:
            while True:
                await asyncio.sleep(3600)  # Keep alive the server
        except asyncio.CancelledError:
            await runner.cleanup()

