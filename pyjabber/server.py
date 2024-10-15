import asyncio
import os
import signal
import socket

from contextlib import closing
from loguru import logger

from pyjabber.db.database import connection
from pyjabber.network.XMLProtocol import XMLProtocol
from pyjabber.network.server.incoming.XMLServerIncomingProtocol import XMLServerIncomingProtocol
from pyjabber.network.server.outcoming.XMLServerOutcomingProtocol import XMLServerOutcomingProtocol
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.QueueMessage import QueueMessage
from pyjabber.webpage.adminPage import admin_instance
from pyjabber.network import CertGenerator

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    """
        Server class

        :param host: Host for the clients connections (localhost by default)
        :param client_port: Port for client connections (5222 by default)
        :param server_port: Port for server-to-server connections (5269 by default)
        :param family: Type of AddressFamily (IPv4 or IPv6)
        :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
        :param enable_tls1_3: Boolean. Enables the use of TLSv1.3 in the STARTTLS process
        :parm cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname
    """
    def __init__(
        self,
        host='localhost',
        client_port=5222,
        server_port=5269,
        server_out_port=5269,
        family=socket.AF_INET,
        connection_timeout=60,
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
        self._adminServer = None
        self._public_ip = None
        self._connection_timeout = connection_timeout
        self._cert_path = cert_path

        # Client handler
        self._enable_tls1_3 = enable_tls1_3
        self._connection_manager = ConnectionManager(self.task_s2s)
        self._queue_message = QueueMessage(self._connection_manager)

    async def run_server(self):
        logger.info("Starting server...")

        if os.path.isfile(os.path.join(SERVER_FILE_PATH, "db", "server.db")) is False:
            logger.debug("No database found. Initializing one...")
            with closing(connection()) as con:
                with open(SERVER_FILE_PATH + "/db/schema.sql", "r") as schema:
                    con.cursor().executescript(schema.read())
                con.commit()

        if CertGenerator.check_hostname_cert_exists(self._host) is False and self._cert_path is None:
            CertGenerator.generate_hostname_cert(self._host)

        loop = asyncio.get_running_loop()

        lan_ip = self.query_local_ip()

        self._client_listener = await loop.create_server(
            lambda: XMLProtocol(
                namespace='jabber:client',
                host=self._host,
                connection_timeout=self._connection_timeout,
                cert_path=self._cert_path,
                queue_message=self._queue_message,
                enable_tls1_3=self._enable_tls1_3,
            ),
            host=[self._host, lan_ip],
            port=self._client_port,
            family=self._family
        )

        logger.info(f"Client domain => {self._host}")
        logger.info(f"Server is listening clients on {[s.getsockname() for s in self._client_listener.sockets]}")

        self._server_listener = await loop.create_server(
            lambda: XMLServerIncomingProtocol(
                namespace='jabber:server',
                host=self._host,
                connection_timeout=self._connection_timeout,
                cert_path=self._cert_path,
                queue_message=self._queue_message,
                enable_tls1_3=self._enable_tls1_3,
            ),
            host=["0.0.0.0"],
            port=self._server_port,
            family=self._family
        )

        logger.info(f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets]}")
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
        loop = asyncio.get_running_loop()

        asyncio.ensure_future(self.server_connection(host, loop), loop=loop)

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
                queue_message=self._queue_message,
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
        except Exception as e:
            logger.error("Unable to retrieve LAN IP")
            raise self.raise_exit()
        finally:
            mock_connection.close()

    def raise_exit(self):
        raise SystemExit(1)

    def start(self, debug: bool = False):
        """
            Start the already created and configuration server
            :param debug: Boolean. Enables debug mode in asyncio
        """
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)

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
