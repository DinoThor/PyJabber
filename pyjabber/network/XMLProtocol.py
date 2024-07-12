import asyncio
import os
import ssl

from loguru import logger
from xml import sax

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLParser import XMLParser

FILE_AUTH = os.path.dirname(os.path.abspath(__file__))


class XMLProtocol(asyncio.Protocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.

    :param namespace: namespace of the XML tags (jabber:client or jabber:server)
    :param host: Host for connections
    :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
    :param connection_manager: Global instance of Connection Manager (Singleton)
    :param cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname
    :param queue_message: Global instance of Queue Message class (Singleton)
    :param enable_tls1_3: Boolean. Enables the use of TLSv1.3 in the STARTTLS process
    """

    def __init__(
            self,
            namespace,
            host,
            connection_timeout,
            connection_manager,
            cert_path,
            queue_message,
            enable_tls1_3=False):

        self._xmlns = namespace
        self._host = host
        self._connection_timeout = connection_timeout
        self._connection_manager: ConnectionManager = connection_manager
        self._cert_path = cert_path
        self._queue_message = queue_message
        self._enable_tls1_3 = enable_tls1_3

        self._transport = None
        self._xml_parser = None
        self._timeout_monitor = None


    def connection_made(self, transport):
        """
        Called when a client or another server opens a TCP connection to the server

        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        """
        if transport:
            self._transport = transport

            self._xml_parser = sax.make_parser()
            self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
            self._xml_parser.setFeature(sax.handler.feature_external_ges, False)
            self._xml_parser.setContentHandler(
                XMLParser(
                    self._host,
                    self._transport,
                    self.task_tls,
                    self._connection_manager,
                    self._queue_message
                )
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection(self._transport.get_extra_info('peername'))

            logger.info(f"Connection from {self._transport.get_extra_info('peername')}")
        else:
            logger.error("Invalid transport")

    def connection_lost(self, exc):
        """
        Called when a client or another server closes a TCP connection to the server

        :param exc: Exception that caused the connection to close
        :type exc: Exception
        """
        logger.info(f"Connection lost from {self._transport.get_extra_info('peername')}: Reason {exc}")

        self._transport = None
        self._xml_parser = None

    def data_received(self, data):
        """
        Called when data is received from the client or another server

        :param data: Chunk of data received
        :type data: Byte array
        """
        try:
            logger.debug(f"Data received from <{hex(id(self._transport))}>: {data.decode()}")
        except:
            logger.debug(f"Binary data recived")

        if self._timeout_monitor:
            self._timeout_monitor.reset()

        '''
        Some XMPP clients/libraries send the XML header
        with the stream stanza all together.
        This can lead sometimes in a exception for the parser.
        An XML header gives no usefull information, as the RFC6120
        takes the vesion 1.0 as standar, so we can remove it safely.
        If I try to remove the header inside the except block, the parser
        keeps refusing it. I'm forced to do always before the feed.
        I probably should change the parser
        '''
        data = data.replace(b"<?xml version=\'1.0\'?>", b"")
        data = data.replace(b"<?xml version=\"1.0\"?>", b"")

        self._xml_parser.feed(data)

    def eof_received(self):
        """
        Called when the client or another server sends an EOF
        """
        peer = self._transport.get_extra_info('peername')

        logger.debug(f"EOF received from {peer}")

        self._connection_manager.disconnection(peer)

    def connection_timeout(self):
        """
        Called when the stream is not responding for a long tikem
        """
        peer = self._transport.get_extra_info('peername')
        logger.debug(f"Connection timeout from {peer}")

        self._transport.write("<connection-timeout/>".encode())
        self._transport.close(peer)

        self._connection_manager.disconnection(peer)

        self._transport = None
        self._xml_parser = None

    ###########################################################################
    ###########################################################################
    ###########################################################################

    def task_tls(self):
        """
            Sync function to call the STARTTLS coroutine
        """
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(self.enable_tls(loop), loop=loop)

    async def enable_tls(self, loop):
        """
            Coroutine to upgrade the connection to TLS
            It swaps the transport for the XMLProtocol, and XMLParser
            :param loop: Running asyncio loop
        """
        parser = self._xml_parser.getContentHandler()

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        if not self._enable_tls1_3:
            ssl_context.options |= ssl.OP_NO_TLSv1_3

        if self._cert_path:
            ssl_context.load_cert_chain(
                certfile=os.path.join(self._cert_path, f"{self._host}_cert.pem"),
                keyfile=os.path.join(self._cert_path, "certs", f"{self._host}_key.pem"),
            )
        else:
            ssl_context.load_cert_chain(
                certfile=os.path.join(FILE_AUTH, "certs", f"{self._host}_cert.pem"),
                keyfile=os.path.join(FILE_AUTH, "certs", f"{self._host}_key.pem"),
            )

        self._transport = await loop.start_tls(
            transport=self._transport,
            protocol=self,
            sslcontext=ssl_context,
            server_side=True)

        parser.buffer = self._transport
        logger.debug(f"Done TLS for <{hex(id(self))}>")
