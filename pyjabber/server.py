import asyncio
import os
import signal
import socket

from contextlib import closing
from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol  import XMLProtocol
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.admin.adminPage import serverInstance

CLIENT_PORT = 5222
CLIENT_NS   = "jabber:client"

SERVER_PORT = 5269
SERVER_NS   = "jabber:server"


class Server():
    _slots__ = [
        "_host",
        "_client_port",
        "_server_port",
        "_family",
        "_client_listener",
        "_server_listener",
        "_connection_timeout",
        "_features"
    ]

    def __init__(
        self,
        host                = "localhost",
        client_port         = CLIENT_PORT,
        server_port         = SERVER_PORT,
        family              = socket.AF_INET,
        connection_timeout  = 60,

    ):
        self._host                  = host
        self._client_port           = client_port
        self._server_port           = server_port
        self._family                = family
        self._client_listener       = None
        self._server_listener       = None
        self._connection_timeout    = connection_timeout

        self._connections           = ConectionsManager()

    async def run_server(self):
        logger.info("Starting server...")

        if os.path.isfile("./pyjabber/db/server.db") is False:
            logger.debug("No database found. Initializing one...")
            with closing(connection()) as con:
                with open("./pyjabber/db/schema.sql", "r") as schema:
                    con.cursor().executescript(schema.read())
                con.commit()

        loop = asyncio.get_running_loop()

        self._client_listener = await loop.create_server(
            lambda: XMLProtocol(
                namespace           = CLIENT_NS,
                connection_timeout  = self._connection_timeout,
            ),
            host    = self._host,
            port    = self._client_port,
            family  = self._family
        )

        logger.info(f"Server is listening clients on {self._client_listener.sockets[0].getsockname()}")

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

    def start(self, debug:bool = False):
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)
        # adminPage = serverInstance()

        try:
            loop.add_signal_handler(signal.SIGINT, self.raise_exit)
            loop.add_signal_handler(signal.SIGABRT, self.raise_exit)
            loop.add_signal_handler(signal.SIGTERM, self.raise_exit)
        except NotImplementedError:  # pragma: no cover
            pass

        try:        
            main_task   = loop.create_task(self.run_server(), name="main_server")
            loop.run_until_complete(main_task)
            loop.run_until_complete(serverInstance())
            loop.run_forever()
            

        except (SystemExit, KeyboardInterrupt):  # pragma: no cover
            pass

        finally:
            # Cancel pending tasks
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions = True))

            #Close admin page
            # adminPage.server_close()

            # Close the server
            close_task = loop.create_task(self.stop(), name="close_server")
            loop.run_until_complete(close_task)
            loop.close()
            asyncio.set_event_loop(None)
