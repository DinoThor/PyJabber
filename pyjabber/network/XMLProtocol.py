import asyncio
import os
import ssl

from loguru import logger
from xml import sax

from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLParser import XMLParser

FILE_AUTH = os.path.dirname(os.path.abspath(__file__))


class XMLProtocol(asyncio.Protocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.
    """

    def __init__(self, namespace, connection_timeout, connection_manager, traefik_certs, queue_message, enable_tls1_3=False):
        self._xmlns = namespace
        self._transport = None
        self._xml_parser = None
        self._timeout_monitor = None
        self._loop = asyncio.get_event_loop()
        self._connection_timeout = connection_timeout
        self._connection_manager = connection_manager

        self._enable_tls1_3 = enable_tls1_3
        self._traefik_certs = traefik_certs
        self._queue_message = queue_message

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
            logger.debug(f"Data received: {data.decode()}")
        except:
            logger.debug(f"Binary data recived")

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
        logger.debug(f"Connection timeout from {self._transport.get_extra_info('peername')}")

        self._transport.write("<connection-timeout/>".encode())
        self._transport.close()

        self._transport = None
        self._xml_parser = None

    ###########################################################################
    ###########################################################################
    ###########################################################################

    def task_tls(self):
        tls = self._loop.create_task(self.enable_tls())
        self._loop.run_until_complete(tls)

    async def enable_tls(self):
        parser = self._xml_parser.getContentHandler()

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        if not self._enable_tls1_3:
            ssl_context.options |= ssl.OP_NO_TLSv1_3

        certfile = "traefik.pem" if self._traefik_certs else "localhost.pem"
        keyfile = "traefik-key.pem" if self._traefik_certs else "localhost-key.pem"

        ssl_context.load_cert_chain(
            certfile=os.path.join(FILE_AUTH, "certs", certfile),
            keyfile=os.path.join(FILE_AUTH, "certs", keyfile),
        )

        new_transport = await self._loop.start_tls(
            transport=self._transport,
            protocol=self,
            sslcontext=ssl_context,
            server_side=True)

        # self._transport.close()
        self._transport = new_transport

        parser.buffer = self._transport
        logger.debug(f"Done TLS")
