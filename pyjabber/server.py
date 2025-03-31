import asyncio
import os
import queue
import signal
import socket
import sqlite3
import ssl

from contextlib import closing

from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol import XMLProtocol, TransportProxy
from pyjabber.network.server.outcoming.XMLServerOutcomingProtocol import XMLServerOutcomingProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.webpage.adminPage import AdminPage
from pyjabber.network import CertGenerator
from pyjabber.metadata import database_in_memory as metadata_database_in_memory
from pyjabber import metadata
from pyjabber.workers import tls_worker, queue_worker

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


def setup_query_local_ip():
    """Return the local IP of the host machine"""
    mock_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        mock_connection.connect(("8.8.8.8", 80))
        local_ip_address = mock_connection.getsockname()[0]
        return local_ip_address
    except OSError as e:
        logger.error(f"Unable to retrieve LAN IP: {e}")
    finally:
        mock_connection.close()


class Server:
    """Server class

    :param host: Host for the clients connections (localhost by default)
    :param client_port: Port for client connections (5222 by default)
    :param server_port: Port for server-to-server connections (5269 by default)
    :param family: Type of AddressFamily (IPv4 or IPv6)
    :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
    :param database_path: Path to the sqlite3 database file. If it does not exist, a new file/database will be created (site-packages/pyjabber/db by default)
    :param database_purge: Flag to indicate the reset process of the database. CAUTION! ALL THE INFORMATION WILL BE LOST
    :param cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname
    """

    def __init__(
        self,
        host: str = "localhost",
        client_port: int = 5222,
        server_port: int = 5269,
        server_out_port: int = 5269,
        family: socket.AddressFamily = socket.AF_INET,
        connection_timeout: int = 60,
        database_path: str = os.path.join(os.getcwd(), "pyjabber.db"),
        database_purge: bool = False,
        database_in_memory: bool = False,
        cert_path: str = None
    ):
        # Server
        self._host = host
        self._client_port = client_port
        self._server_port = server_port
        self._server_out_port = server_out_port
        self._family = family
        self._client_listener = None
        self._server_listener = None
        self._adminServer = AdminPage()
        self._public_ip = None
        self._connection_timeout = connection_timeout

        # Database
        self._database_path = database_path
        self._sql_init_script = os.path.join(SERVER_FILE_PATH, "db", "schema.sql")
        self._sql_delete_script = os.path.join(SERVER_FILE_PATH, "db", "delete.sql")
        self._database_purge = database_purge
        self._database_in_memory = database_in_memory
        self._db_in_memory_con = None

        # Certs
        self._cert_path = cert_path or os.path.join(SERVER_FILE_PATH, "network", "certs")

        # Singletons
        self._connection_manager = ConnectionManager()

        # Contextvar
        metadata.host.set(host)
        metadata.database_path.set(self._database_path)
        metadata.config_path.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/config.yaml"))
        metadata.cert_path.set(self._cert_path)
        metadata.root_path.set(SERVER_FILE_PATH)

        # Flags
        self._ready = asyncio.Event()

    @property
    def ready(self):
        return self._ready

    def setup_database(self):
        if self._database_in_memory:
            logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
            self._db_in_memory_con = sqlite3.connect("file::memory:?cache=shared", uri=True)
            with open(self._sql_init_script, "r") as script:
                self._db_in_memory_con.cursor().executescript(script.read())
                self._db_in_memory_con.commit()
            metadata_database_in_memory.set(self._database_in_memory)

        elif os.path.isfile(self._database_path) is False:
            logger.info("No database found. Initializing one...")
            if self._database_purge:
                logger.info("Ignoring purge database flag. No DB to purge")
            with closing(connection()) as con:
                with open(self._sql_init_script, "r") as script:
                    con.cursor().executescript(script.read())
                con.commit()
        else:
            if self._database_purge:
                logger.info("Resetting the database to default state...")
                with closing(connection()) as con:
                    with open(self._sql_delete_script, "r") as script:
                        con.cursor().executescript(script.read())
                    con.commit()

    def setup_certs(self):
        try:
            if CertGenerator.check_hostname_cert_exists(self._host, self._cert_path) is False:
                CertGenerator.generate_hostname_cert(self._host, self._cert_path)
        except FileNotFoundError as e:
            logger.error(f"{e.__class__.__name__}: Pass an existing directory in your system to load the certs. "
                         f"Closing server")
            raise SystemExit

    async def setup_tls_worker(self):
        """
        A TLS Worker for process STARTTLS petitions.
        A global Asyncio queue must be declared and used across the server. The main producer of the queue will be the
        XMLProtocol class, where the transport/buffer/protocol is managed.
        The worker is global for all the server components, and it can be duplicated across multiple workers in
        different threads to handle a high number of new connections established within a very short period of time.

        """
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile=os.path.join(self._cert_path, f"{self._host}_cert.pem"),
            keyfile=os.path.join(self._cert_path, f"{self._host}_key.pem"),
        )
        loop = asyncio.get_running_loop()
        try:
            while True:
                transport, protocol, parser = await tls_queue.get()
                peer = transport.get_extra_info("peername")
                try:
                    new_transport = await loop.start_tls(
                        transport=transport.originalTransport,
                        protocol=protocol,
                        sslcontext=ssl_context,
                        server_side=True)

                    new_transport = TransportProxy(new_transport, peer)
                    transport = new_transport
                    parser.buffer = new_transport
                    logger.debug(f"Done TLS for <{peer}>")

                except ConnectionResetError:
                    logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
                    if not transport.is_closing():
                        self._connection_manager.close(peer)
        except asyncio.CancelledError:
            pass

    async def run_server(self):
        """
        Launches the configured server, and returns a coroutine.
        """
        logger.info("Starting server...")

        self.setup_database()
        self.setup_certs()
        lan_ip = setup_query_local_ip()

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

        # try:
        #     self._server_listener = await loop.create_server(
        #         lambda: XMLServerIncomingProtocol(
        #             namespace="jabber:server",
        #             host=self._host,
        #             connection_timeout=self._connection_timeout,
        #             cert_path=self._cert_path,
        #         ),
        #         host=["0.0.0.0"],
        #         port=self._server_port,
        #         family=self._family
        #     )
        # except OSError as e:
        #     logger.error(e)
        #     raise SystemExit

        # logger.info(f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets if s]}")
        logger.success("Server started...")
        self._ready.set()

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

    # def task_s2s(self, host):
    #     # host = host.split("@")[-1]
    #     # loop = asyncio.get_running_loop()
    #     #
    #     # asyncio.ensure_future(self.server_connection(host, loop), loop=loop)

    # async def server_connection(self, remote_host, loop):
    #     """Task to connect to another XMPP server
    #     :param remote_host: Host of the remote server to connect
    #     :param loop: Asyncio running loop. Necessary to perform task
    #     """
    #     await loop.create_connection(
    #         lambda: XMLServerOutcomingProtocol(
    #             namespace="jabber:server",
    #             host=remote_host,
    #             public_host=self._public_ip,
    #             connection_timeout=self._connection_timeout,
    #         ),
    #         host=remote_host,
    #         port=self._server_out_port
    #     )

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
            server_task = asyncio.create_task(self.run_server())
            tasks = [
                asyncio.create_task(self._adminServer.start()),
                asyncio.create_task(tls_worker()),
                asyncio.create_task(queue_worker())
            ]
            await asyncio.gather(*tasks)

        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError) as e:  # pragma: no cover
            logger.trace(f"Signal {e.__class__.__name__} intercepted. Stopping server")

        finally:
            for task in tasks:
                task.cancel()
            try:
                await asyncio.gather(*tasks, return_exceptions=False)
                await self.stop_server()
            except (asyncio.CancelledError, SystemExit, Exception) as e:
                pass
