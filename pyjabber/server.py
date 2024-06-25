import asyncio
import os
import signal
import socket
import nest_asyncio
import urllib.request
import wget

from contextlib import closing
from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.network.server.incoming.XMLServerIncomingProtocol import XMLServerIncomingProtocol
from pyjabber.network.server.outcoming.XMLServerOutcomingProtocol import XMLServerOutcomingProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.QueueMessage import QueueMessage
from pyjabber.webpage.adminPage import admin_instance

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    def __init__(
        self,
        host="localhost",
        client_port=5222,
        server_port=5269,
        family=socket.AF_INET,
        connection_timeout=60,
        enable_tls1_3=False,
        traefik_certs=False
    ):
        # Server
        self._host = host
        self._client_port = client_port
        self._server_port = server_port
        self._family = family
        self._client_listener = None
        self._server_listener = None
        self._adminServer = None
        self._connection_timeout = connection_timeout

        # Client handler
        self._enable_tls1_3 = enable_tls1_3
        self._traefik_certs = traefik_certs
        self._connection_manager = ConnectionManager(self.task_s2s)
        self._queue_message = QueueMessage(self._connection_manager)

    async def run_server(self):
        logger.info("Starting server...")

        if os.path.isfile(os.path.join(SERVER_FILE_PATH + "/db/server.db")) is False:
            logger.debug("No database found. Initializing one...")
            with closing(connection()) as con:
                with open(SERVER_FILE_PATH + "/db/schema.sql", "r") as schema:
                    con.cursor().executescript(schema.read())
                con.commit()

        if self._traefik_certs:
            if not os.path.isfile(os.path.join(SERVER_FILE_PATH, "network", "certs", "traefik.pem")):
                wget.download("http://traefik.me/fullchain.pem", os.path.join(SERVER_FILE_PATH, "network", "certs", "traefik.pem"))
            if not os.path.isfile(os.path.join(SERVER_FILE_PATH, "network", "certs", "traefik-key.pem")):
                wget.download("http://traefik.me/privkey.pem", os.path.join(SERVER_FILE_PATH, "network", "certs", "traefik-key.pem"))

        loop = asyncio.get_event_loop()

        self._client_listener = await loop.create_server(
            lambda: XMLProtocol(
                namespace='jabber:client',
                connection_timeout=self._connection_timeout,
                connection_manager=self._connection_manager,
                enable_tls1_3=self._enable_tls1_3,
                traefik_certs=self._traefik_certs,
                queue_message=self._queue_message
            ),
            host=self._host,
            port=self._client_port,
            family=self._family
        )


        logger.info(f"Server is listening clients on {self._client_listener.sockets[0].getsockname()}")

        self._server_listener = await loop.create_server(
            lambda: XMLServerIncomingProtocol(
                namespace='jabber:server',
                connection_timeout=self._connection_timeout,
                connection_manager=self._connection_manager,
                enable_tls1_3=self._enable_tls1_3,
                traefik_certs=self._traefik_certs,
                queue_message=self._queue_message
            ),
            host=self._host,
            port=self._server_port,
            family=self._family
        )

        logger.info(f"Server is listening servers on {self._server_listener.sockets[0].getsockname()}")

        public_ip = urllib.request.urlopen("https://api.ipify.org/")
        if public_ip.status == 200:
            public_ip = public_ip.read().decode()
            logger.info(f"SERVER DOMAIN NAME ==> https://{public_ip.replace('.', '-')}.traefik.me")

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

    def task_s2s(self, host):
        host = host.split("@")[-1]
        asyncio.get_running_loop().create_task(self.server_connection(host))

    async def server_connection(self, host):
        loop = asyncio.get_event_loop()

        await loop.create_connection(
            lambda: XMLServerOutcomingProtocol(
                namespace="jabber:server",
                host=host,
                connection_timeout=self._connection_timeout,
                connection_manager=self._connection_manager,
                queue_message=self._queue_message,
                enable_tls1_3=self._enable_tls1_3,
                traefik_certs=self._traefik_certs
            ),
            host=host,
            port=5269
        )

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
            # XMPP Server
            main_server = loop.create_task(self.run_server())
            loop.run_until_complete(main_server)

            # Control Panel Webpage | localhost:9090
            admin_server = admin_instance()
            loop.run_until_complete(admin_server)

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
