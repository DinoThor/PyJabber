import asyncio
import multiprocessing
import os
import signal
import ssl
from concurrent.futures.process import ProcessPoolExecutor

from loguru import logger

from pyjabber import AppConfig
from pyjabber.db.database import DB
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.http_server import HttpServer
from pyjabber.network import CertGenerator
from pyjabber.network.protocols.XMLProtocol import XMLProtocol
from pyjabber.plugins.xep_0060.xep_0060 import PubSub
from pyjabber.plugins.xep_0363.upload_server import UploadHttpServer
from pyjabber.plugins.xep_0363.xep_0363 import HTTPFieldUpload
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.queues.workers.MessageQueueWorker import queue_worker
from pyjabber.queues.workers.ServerConnectionWorker import server_connection_worker
from pyjabber.server_parameters import Parameters
from pyjabber.utils.ServerUtils import setup_ip_by_host, setup_query_local_ip
from pyjabber.webpage.adminPage import api_adminpage_app

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Server:
    """Server class

    :param param: Instance of Parameter class, with all the configuration available for the protocols. If not provided,
    a default profile will be loaded
    """

    def __init__(self, param: Parameters = Parameters()):
        # Server
        self._host = param.host
        self._public_ip = setup_query_local_ip()
        self._host_ip = setup_ip_by_host(self._host)
        self._client_port = param.client_port
        self._server_port = param.server_port
        self._family = param.family
        self._client_listener = None
        self._server_listener = None
        self._http_server = None
        self._http_apps = []
        self._connection_timeout = param.connection_timeout
        self._database_in_memory = param.database_in_memory

        # Certs
        cert_path = param.cert_path or os.path.join(
            SERVER_FILE_PATH, "network", "certs"
        )
        try:
            if not CertGenerator.check_hostname_cert_exists(param.host, cert_path):
                CertGenerator.generate_hostname_cert(param.host, param.cert_path)
        except FileNotFoundError as e:
            logger.error(
                f"{e.__class__.__name__}: Pass an existing directory in your system to load the certs. "
                f"Closing protocols"
            )
            raise SystemExit

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile=os.path.join(cert_path, f"{param.host}_cert.pem"),
            keyfile=os.path.join(cert_path, f"{param.host}_key.pem"),
        )

        ssl_context_s2s = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context_s2s.check_hostname = False
        ssl_context_s2s.verify_mode = ssl.CERT_NONE
        ssl_context_s2s.load_cert_chain(
            certfile=os.path.join(cert_path, f"{param.host}_cert.pem"),
            keyfile=os.path.join(cert_path, f"{param.host}_key.pem"),
        )

        AppConfig.app_config = AppConfig.AppConfig(
            host=param.host,
            ip=[self._host_ip, self._public_ip],
            ssl_context=ssl_context,
            ssl_context_s2s=ssl_context_s2s,
            connection_timeout=param.connection_timeout,
            family=self._family,
            server_port=self._server_port,
            database_path=param.database_path,
            database_purge=param.database_purge,
            database_in_memory=self._database_in_memory,
            database_debug=param.database_debug,
            config_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "config/config.yaml"
            ),
            cert_path=cert_path,
            root_path=SERVER_FILE_PATH,
            message_persistence=param.message_persistence or False,
            semaphore=asyncio.Semaphore(multiprocessing.cpu_count()),
            process_pool_exe=ProcessPoolExecutor(multiprocessing.cpu_count()),
            verbose=param.verbose,
            plugins=param.plugins,
            items=param.items,
        )

        # HTTP Server
        if "urn:xmpp:http:upload:0" in param.plugins and "upload.$" in param.items:
            self._http_apps.append(api_adminpage_app())
            self._UploadHttpServer = UploadHttpServer()
            self._http_apps.append(self._UploadHttpServer.get_aiohttp_webapp())
            HTTPFieldUpload(self._UploadHttpServer)

            self._http_server = HttpServer(self._http_apps)

        # Flags
        self._ready = asyncio.Event()

    @property
    def ready(self):
        return self._ready

    async def run_server(self):
        """
        Launches the configured protocols, and returns a coroutine.
        """
        try:
            logger.info("Starting protocols...")

            await DB.setup_database()
            if not self._database_in_memory:
                DB.run_db_migrations()

            presence = Presence()
            await presence.get_all_pending_presence()

            pubsub = PubSub()
            await pubsub.update_memory_from_database()

            loop = asyncio.get_running_loop()

            try:
                self._client_listener = await loop.create_server(
                    lambda: XMLProtocol(
                        namespace="jabber:client",
                        connection_timeout=self._connection_timeout,
                    ),
                    host=[self._host, self._public_ip]
                    if self._public_ip
                    else [self._host],
                    port=self._client_port,
                    family=self._family,
                )
            except OSError as e:
                logger.error(e)
                self.raise_exit()

            logger.info(f"Client domain => {self._host}")
            logger.info(
                f"Server is listening clients on {[s.getsockname() for s in self._client_listener.sockets if s]}"
            )

            try:
                self._server_listener = await loop.create_server(
                    lambda: XMLProtocol(
                        namespace="jabber:server",
                        connection_timeout=self._connection_timeout,
                    ),
                    host=[self._host, self._public_ip]
                    if self._public_ip
                    else [self._host],
                    port=self._server_port,
                    family=self._family,
                )
            except OSError as e:
                logger.error(e)
                raise SystemExit

            logger.info(
                f"Server is listening servers on {[s.getsockname() for s in self._server_listener.sockets if s]}"
            )
            logger.success("Server started...")
            self._ready.set()

            while True:
                # Keep the coroutine alive, in order to catch the CancelledError exception
                await asyncio.sleep(3600)

        except asyncio.CancelledError:
            logger.info("Stopping server...")

            await DB.close_engine_async()

            if self._client_listener and self._client_listener.is_serving():
                self._client_listener.close()
                await self._client_listener.wait_closed()

            if self._server_listener and self._server_listener.is_serving():
                self._server_listener.close()
                await self._server_listener.wait_closed()

            logger.success("Server stopped...")

    @staticmethod
    def raise_exit(*args) -> Exception:
        """Exception used to signal the safe close of the server"""
        raise SystemExit(1)

    async def start(self):
        """Start the already created and configuration server"""
        _ = get_queue(QueueName.CONNECTIONS)
        _ = get_queue(QueueName.MESSAGES)
        _ = get_queue(QueueName.SERVERS)

        signal.signal(signal.SIGINT, self.raise_exit)
        signal.signal(signal.SIGABRT, self.raise_exit)
        signal.signal(signal.SIGTERM, self.raise_exit)

        tasks = None

        try:
            tasks = [
                asyncio.create_task(queue_worker()),
                asyncio.create_task(server_connection_worker()),
                asyncio.create_task(self.run_server()),
            ]

            if self._http_server:
                tasks.append(asyncio.create_task(self._http_server.start()))

            await asyncio.gather(*tasks)

        except (
            SystemExit,
            KeyboardInterrupt,
            asyncio.CancelledError,
        ) as e:  # pragma: no cover
            logger.trace(f"Signal {e.__class__.__name__} intercepted. Stopping server")

        finally:
            for task in tasks:
                _ = task.cancel()

            await asyncio.gather(*tasks)
