import asyncio
import os
import signal

from loguru import logger

from pyjabber import init_utils
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.network.server.incoming.XMLServerIncomingProtocol import XMLServerIncomingProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.server_parameters import Parameters
from pyjabber.webpage.adminPage import AdminPage
from pyjabber import metadata
from pyjabber.workers import tls_worker, queue_worker

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    """Server class

    :param param: Instance of Parameter class, with all the configuration available for the server. If not provided,
    a default profile will be loaded
    """

    def __init__(self, param: Parameters = Parameters()):
        # Server
        self._host = param.host
        self._client_port = param.client_port
        self._server_port = param.server_port
        self._server_out_port = param.server_out_port
        self._family = param.family
        self._client_listener = None
        self._server_listener = None
        self._adminServer = AdminPage()
        self._public_ip = None
        self._connection_timeout = param.connection_timeout

        # Database
        self._database_path = param.database_path
        self._sql_init_script = os.path.join(SERVER_FILE_PATH, "db", "schema.sql")
        self._sql_delete_script = os.path.join(SERVER_FILE_PATH, "db", "delete.sql")
        self._database_purge = param.database_purge
        self._database_in_memory = param.database_in_memory
        self._db_in_memory_con = None

        # Certs
        self._cert_path = param.cert_path or os.path.join(SERVER_FILE_PATH, "network", "certs")

        # Singletons
        self._connection_manager = ConnectionManager()

        # Contextvar
        metadata.host.set(param.host)
        metadata.database_path.set(self._database_path)
        metadata.config_path.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/config.yaml"))
        metadata.cert_path.set(self._cert_path)
        metadata.root_path.set(SERVER_FILE_PATH)

        # Flags
        self._ready = asyncio.Event()

    @property
    def ready(self):
        return self._ready

    async def run_server(self):
        """
        Launches the configured server, and returns a coroutine.
        """
        try:
            logger.info("Starting server...")

            init_utils.setup_database(
                self._database_in_memory,
                self._database_path,
                self._database_purge,
                self._sql_init_script,
                self._sql_delete_script
            )
            init_utils.setup_certs(self._host, self._cert_path)
            lan_ip = init_utils.setup_query_local_ip()

            loop = asyncio.get_running_loop()

            try:
                self._client_listener = await loop.create_server(
                    lambda: XMLProtocol(
                        namespace="jabber:client",
                        host=self._host,
                        connection_timeout=self._connection_timeout,
                        cert_path=self._cert_path,
                    ),
                    host=[self._host, lan_ip] if lan_ip else [self._host],
                    port=self._client_port,
                    family=self._family
                )
            except OSError as e:
                logger.error(e)
                self.raise_exit()

            logger.info(f"Client domain => {self._host}")
            logger.info(f"Server is listening clients on {[s.getsockname() for s in self._client_listener.sockets if s]}")

            try:
                self._server_listener = await loop.create_server(
                    lambda: XMLServerIncomingProtocol(
                        namespace="jabber:server",
                        host=self._host,
                        connection_timeout=self._connection_timeout,
                        cert_path=self._cert_path,
                    ),
                    host=["0.0.0.0"],
                    port=self._server_port,
                    family=self._family
                )
            except OSError as e:
                logger.error(e)
                raise SystemExit

            logger.info(f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets if s]}")
            logger.success("Server started...")
            self._ready.set()

            while True:
                # Keep the coroutine alive, in order to catch the CancelledError exception
                await asyncio.sleep(3600)

        except asyncio.CancelledError:
            logger.info("Stopping server...")

            if self._db_in_memory_con:
                self._db_in_memory_con.close()

            if self._client_listener and self._client_listener.is_serving():
                self._client_listener.close()
                await self._client_listener.wait_closed()

            if self._server_listener and self._server_listener.is_serving():
                self._server_listener.close()
                await self._server_listener.wait_closed()

            logger.success("Server stopped...")

    async def stop_server(self):
        """
        Safely stops the running server
        """
        logger.info("Stopping server...")

        if self._db_in_memory_con:
            self._db_in_memory_con.close()

        if self._client_listener and self._client_listener.is_serving():
            self._client_listener.close()
            await self._client_listener.wait_closed()

        if self._server_listener and self._server_listener.is_serving():
            self._server_listener.close()
            await self._server_listener.wait_closed()

        logger.success("Server stopped...")

    def raise_exit(self, *args):
        """Exception used to signal the safe close of the server"""
        raise SystemExit(1)

    async def start(self):
        """Start the already created and configuration server"""
        metadata.tls_queue.set(asyncio.Queue())
        metadata.connection_queue.set(asyncio.Queue())
        metadata.message_queue.set(asyncio.Queue())

        signal.signal(signal.SIGINT, self.raise_exit)
        signal.signal(signal.SIGABRT, self.raise_exit)
        signal.signal(signal.SIGTERM, self.raise_exit)

        try:
            tasks = [
                asyncio.create_task(self._adminServer.start()),
                asyncio.create_task(tls_worker()),
                asyncio.create_task(queue_worker()),
                asyncio.create_task(self.run_server())
            ]
            await asyncio.gather(*tasks)

        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError) as e:  # pragma: no cover
            logger.trace(f"Signal {e.__class__.__name__} intercepted. Stopping server")

        finally:
            for task in tasks:
                _ = task.cancel()

            await asyncio.gather(*tasks)
