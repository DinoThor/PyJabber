import asyncio
import os
import queue
import signal
import socket
import sqlite3
import ssl
import sys

from contextlib import closing
from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.network.server.incoming.XMLServerIncomingProtocol import XMLServerIncomingProtocol
from pyjabber.network.server.outcoming.XMLServerOutcomingProtocol import XMLServerOutcomingProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.tls.TLSWorker import TLSQueue
from pyjabber.stream.QueueMessage import QueueMessage
from pyjabber.webpage.adminPage import AdminPage
from pyjabber.network import CertGenerator
from pyjabber.metadata import host as metadata_host, config_path as metadata_config_path
from pyjabber.metadata import database_path as metadata_database_path, root_path as metadata_root_path
from pyjabber.metadata import database_in_memory as metadata_database_in_memory

if sys.platform == "win32":
    #from winloop import run
    pass
else:
    import uvloop

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    """
        Server class

        :param host: Host for the clients connections (localhost by default)
        :param client_port: Port for client connections (5222 by default)
        :param server_port: Port for server-to-server connections (5269 by default)
        :param family: Type of AddressFamily (IPv4 or IPv6)
        :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
        :param database_path: Path to the sqlite3 database file. If it does not exist, a new file/database will be created (site-packages/pyjabber/db by default)
        :param database_purge: Flag to indicate the reset process of the database. CAUTION! ALL THE INFORMATION WILL BE LOST
        :param enable_tls1_3: Boolean. Enables the use of TLSv1.3 in the STARTTLS process
        :param cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname
    """

    def __init__(
        self,
        host="localhost",
        client_port=5222,
        server_port=5269,
        server_out_port=5269,
        family=socket.AF_INET,
        connection_timeout=60,
        database_path=os.path.join(os.getcwd(), "pyjabber.db"),
        database_purge=False,
        database_in_memory=False,
        enable_tls1_3=False,
        cert_path=None
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
        self._database_path = database_path
        self._sql_init_script = os.path.join(SERVER_FILE_PATH, "db", "schema.sql")
        self._sql_delete_script = os.path.join(SERVER_FILE_PATH, "db", "delete.sql")
        self._database_purge = database_purge
        self._database_in_memory = database_in_memory
        self._db_in_memory_con = None
        self._cert_path = cert_path or os.path.join(SERVER_FILE_PATH, "network", "certs")
        self._custom_loop = True

        # Client handler
        self._enable_tls1_3 = enable_tls1_3

        # Singletons
        self._connection_manager = ConnectionManager(self.task_s2s)
        self._queue_message = QueueMessage(self._connection_manager)

        metadata_host.set(host)
        metadata_database_path.set(self._database_path)
        metadata_config_path.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/config.yaml"))
        metadata_root_path.set(SERVER_FILE_PATH)
        metadata_database_in_memory.set(False)

    async def run_server(self):
        logger.info("Starting server...")

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

        try:
            if CertGenerator.check_hostname_cert_exists(self._host, self._cert_path) is False:
                CertGenerator.generate_hostname_cert(self._host, self._cert_path)
        except FileNotFoundError as e:
            logger.error(e)
            logger.error("Pass an existing directory in your system to load the certs")
            logger.error("Closing server")
            raise SystemExit

        loop = asyncio.get_running_loop()

        lan_ip = self.query_local_ip()

        try:
            self._client_listener = await loop.create_server(
                lambda: XMLProtocol(
                    namespace="jabber:client",
                    host=self._host,
                    connection_timeout=self._connection_timeout,
                    cert_path=self._cert_path,
                    enable_tls1_3=self._enable_tls1_3,
                ),
                host=[self._host, lan_ip] if lan_ip else [self._host],
                port=self._client_port,
                family=self._family
            )
        except OSError as e:
            logger.error(e)
            raise SystemExit


        logger.info(f"Client domain => {self._host}")
        logger.info(f"Server is listening clients on {[s.getsockname() for s in self._client_listener.sockets if s]}")

        try:
            self._server_listener = await loop.create_server(
                lambda: XMLServerIncomingProtocol(
                    namespace="jabber:server",
                    host=self._host,
                    connection_timeout=self._connection_timeout,
                    cert_path=self._cert_path,
                    enable_tls1_3=self._enable_tls1_3,
                ),
                host=["0.0.0.0"],
                port=self._server_port,
                family=self._family
            )
        except OSError as e:
            logger.error(e)
            raise SystemExit

        logger.info(f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets if s]}")
        logger.info("Server started...")

    async def stop(self):
        logger.info("Stopping server...")

        if self._db_in_memory_con:
            self._db_in_memory_con.close()

        if self._client_listener and self._client_listener.is_serving():
            self._client_listener.close()
            await self._client_listener.wait_closed()

        if self._server_listener and self._server_listener.is_serving():
            self._server_listener.close()
            await self._server_listener.wait_closed()

        logger.info("Server stopped...")

    def task_s2s(self, host):
        host = host.split("@")[-1]
        loop = asyncio.get_running_loop()

        asyncio.ensure_future(self.server_connection(host, loop), loop=loop)

    async def tls_worker(self, tls_queue: queue.Queue):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        if not self._enable_tls1_3:
            ssl_context.options |= ssl.OP_NO_TLSv1_3

        ssl_context.load_cert_chain(
            certfile=os.path.join(self._cert_path, f"{self._host}_cert.pem"),
            keyfile=os.path.join(self._cert_path, f"{self._host}_key.pem"),
        )

        loop = asyncio.get_running_loop()

        try:
            while True:
                transport, protocol, parser = await tls_queue.get()
                old_peer = transport.get_extra_info("peername")
                try:
                    new_transport = await loop.start_tls(
                        transport=transport,
                        protocol=protocol,
                        sslcontext=ssl_context,
                        server_side=True)

                    transport = new_transport
                    parser.buffer = new_transport
                    logger.debug(f"Done TLS for <{old_peer}>")

                except ConnectionResetError:
                    logger.error(f"ERROR DURING TLS UPGRADE WITH <{old_peer}>")
                    if not transport.is_closing():
                        self._connection_manager.close(old_peer)
        except asyncio.CancelledError:
            pass

    async def server_connection(self, remote_host, loop):
        """
            Task to connect to another XMPP server
            :param remote_host: Host of the remote server to connect
            :param loop: Asyncio running loop. Necessary to perform task
        """
        await loop.create_connection(
            lambda: XMLServerOutcomingProtocol(
                namespace="jabber:server",
                host=remote_host,
                public_host=self._public_ip,
                connection_timeout=self._connection_timeout,
                enable_tls1_3=self._enable_tls1_3,
            ),
            host=remote_host,
            port=self._server_out_port
        )

    def query_local_ip(self):
        """
            Return the local IP of the host machine
        """
        mock_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            mock_connection.connect(("8.8.8.8", 80))
            local_ip_address = mock_connection.getsockname()[0]
            return local_ip_address
        except OSError as e:
            logger.error(f"Unable to retrieve LAN IP: {e}")
        finally:
            mock_connection.close()

    def raise_exit(self, *args):
        raise SystemExit(1)

    async def start(self):
        """
            Start the already created and configuration server
            :param debug: Boolean. Enables debug mode in asyncio
        """

        signal.signal(signal.SIGINT, self.raise_exit)
        signal.signal(signal.SIGABRT, self.raise_exit)
        signal.signal(signal.SIGTERM, self.raise_exit)

        tls_queue = TLSQueue().queue

        try:
            main_server = asyncio.create_task(self.run_server())
            admin_coro = self._adminServer.start()
            tls_task = asyncio.create_task(self.tls_worker(tls_queue))
            await asyncio.gather(main_server, admin_coro, tls_task)

        except (SystemExit, KeyboardInterrupt):  # pragma: no cover
            pass

        finally:
            tls_task.cancel()
            await asyncio.gather(self.stop(), self._adminServer.app.cleanup())
