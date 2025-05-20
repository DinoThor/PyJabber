import asyncio
import os
import signal

from loguru import logger

from pyjabber import init_utils
from pyjabber.db.database import DB
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
        self._public_ip = init_utils.setup_query_local_ip()
        self._host_ip = init_utils.setup_ip_by_host(self._host)
        self._client_port = param.client_port
        self._server_port = param.server_port
        self._server_out_port = param.server_out_port
        self._family = param.family
        self._client_listener = None
        self._server_listener = None
        self._adminServer = AdminPage()
        self._connection_timeout = param.connection_timeout

        # Database
        self._database_path = param.database_path
        self._database_purge = param.database_purge
        self._database_in_memory = param.database_in_memory

        # Certs
        self._cert_path = param.cert_path or os.path.join(SERVER_FILE_PATH, "network", "certs")

        # Singletons
        self._connection_manager = ConnectionManager()

        # Global constants to use across the server modules/classes
        metadata.init_config(
            host=param.host,
            ip=[self._host_ip, self._public_ip],
            database_path=self._database_path,
            database_purge=self._database_purge,
            database_in_memory=self._database_in_memory,
            config_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/config.yaml"),
            cert_path=self._cert_path,
            root_path=SERVER_FILE_PATH,
            message_persistence=param.message_persistence or False,
            plugins=param.plugins,
            items=param.items
        )

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

            engine = DB.setup_database()
            if not self._database_in_memory:
                DB.run_db_migrations()
            # if not self._database_in_memory and DB.needs_upgrade(engine):
            #     DB.run_migrations_if_needed()
            self._public_ip = init_utils.setup_query_local_ip()

            loop = asyncio.get_running_loop()

            try:
                self._client_listener = await loop.create_server(
                    lambda: XMLProtocol(
                        namespace="jabber:client",
                        host=self._host,
                        connection_timeout=self._connection_timeout,
                        cert_path=self._cert_path,
                    ),
                    host=[self._host, self._public_ip] if self._public_ip else [self._host],
                    port=self._client_port,
                    family=self._family
                )
            except OSError as e:
                logger.error(e)
                self.raise_exit()

            logger.info(f"Client domain => {self._host}")
            logger.info(
                f"Server is listening clients on {[s.getsockname() for s in self._client_listener.sockets if s]}")

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

            logger.info(
                f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets if s]}")
            logger.success("Server started...")
            self._ready.set()

            while True:
                # Keep the coroutine alive, in order to catch the CancelledError exception
                await asyncio.sleep(3600)

        except asyncio.CancelledError:
            logger.info("Stopping server...")

            DB.close_engine()

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
        metadata.TLS_QUEUE = asyncio.Queue()
        metadata.CONNECTION_QUEUE = asyncio.Queue()
        metadata.MESSAGE_QUEUE = asyncio.Queue()

        signal.signal(signal.SIGINT, self.raise_exit)
        signal.signal(signal.SIGABRT, self.raise_exit)
        signal.signal(signal.SIGTERM, self.raise_exit)

        tasks = None

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
