import asyncio
import dataclasses
import os
import signal
import socket
import nest_asyncio

from contextlib import closing
from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.utils import Singleton
from pyjabber.webpage.adminPage import serverInstance

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    def __init__(
        self,
        host="localhost",
        client_port=5222,
        server_port=5269,
        family=socket.AF_INET,
        connection_timeout=60,
    ):
        self._host = host
        self._client_port = client_port
        self._server_port = server_port
        self._family = family
        self._client_listener = None
        self._server_listener = None
        self._adminServer = None
        self._connection_timeout = connection_timeout

        self._connection_manager = ConnectionManager()

    async def run_server(self):
        logger.info("Starting server...")

        if os.path.isfile(os.path.join(SERVER_FILE_PATH + "/db/server.db")) is False:
            logger.debug("No database found. Initializing one...")
            with closing(connection()) as con:
                with open(SERVER_FILE_PATH + "/db/schema.sql", "r") as schema:
                    con.cursor().executescript(schema.read())
                con.commit()

        loop = asyncio.get_event_loop()

        self._client_listener = await loop.create_server(
            lambda: XMLProtocol(
                namespace='jabber:client',
                connection_timeout=self._connection_timeout,
                connection_manager=self._connection_manager
            ),
            host=self._host,
            port=self._client_port,
            family=self._family
        )

        logger.info(f"Server is listening clients on {self._client_listener.sockets[0].getsockname()}")

        self._server_listener = await loop.create_server(
            lambda: XMLProtocol(
                namespace='jabber:server',
                connection_timeout=self._connection_timeout,
                connection_manager=self._connection_manager
            ),
            host=self._host,
            port=self._server_port,
            family=self._family
        )

        logger.info(f"Server is listening servers on {self._server_listener.sockets[0].getsockname()}")

        logger.info("Server started...")

    async def stop(self):
        logger.info("Stopping server...")

        if self._client_listener and self._client_listener.is_serving():
            self._client_listener.close()
            await self._client_listener.wait_closed()

        if self._server_listener and self._server_listener.is_serving():
            self._server_listener.close()
            await self._server_listener.wait_closed()

        logger.info("Server stopped...")

    def raise_exit(self):
        raise SystemExit(1)

    def start(self, debug: bool = False):
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)

        nest_asyncio.apply(loop)

        try:
            loop.add_signal_handler(signal.SIGINT, self.raise_exit)
            loop.add_signal_handler(signal.SIGABRT, self.raise_exit)
            loop.add_signal_handler(signal.SIGTERM, self.raise_exit)
        except NotImplementedError:  # pragma: no cover
            pass

        try:
            main_task = loop.create_task(self.run_server())
            loop.run_until_complete(main_task)
            loop.run_until_complete(serverInstance())
            # loop.run_forever()

        except (SystemExit, KeyboardInterrupt):  # pragma: no cover
            pass

        finally:
            # Cancel pending tasks
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

            # Close the server
            close_task = loop.create_task(self.stop())
            loop.run_until_complete(close_task)
            loop.close()
            asyncio.set_event_loop(None)
