import os
import ssl
from xml import sax

from loguru import logger

from pyjabber.network.server.outcoming.XMLServerOutcomingParser import (
    XMLServerOutcomingParser,
)
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLProtocol import XMLProtocol

FILE_AUTH = os.path.dirname(os.path.abspath(__file__))


class XMLServerOutcomingProtocol(XMLProtocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.
    """

    def __init__(
            self,
            namespace,
            host,
            connection_manager,
            queue_message,
            traefik_certs=False,
            enable_tls1_3=False,
            connection_timeout=None):

        super().__init__(
            namespace,
            connection_timeout,
            connection_manager,
            traefik_certs,
            queue_message,
            enable_tls1_3)
        self._host = host

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
            self._xml_parser.setFeature(
                sax.handler.feature_external_ges, False)
            self._xml_parser.setContentHandler(
                XMLServerOutcomingParser(
                    self._transport,
                    self.task_tls,
                    self._connection_manager,
                    self._queue_message,
                    self._host)
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection_server(
                self._transport.get_extra_info('peername'), self._host, self._transport)

            logger.info(
                f"Server connection to {self._transport.get_extra_info('peername')}")

        else:
            logger.error("Invalid transport")

    def eof_received(self):
        """
        Called when the client or another server sends an EOF
        """
        peer = self._transport.get_extra_info('peername')

        logger.debug(f"EOF received from {peer}")

        self._connection_manager.disconnection_server(peer)

        self._transport = None
        self._xml_parser = None

    ###########################################################################
    ###########################################################################
    ###########################################################################
    async def enable_tls(self):
        parser = self._xml_parser.getContentHandler()

        certfile = "_wildcard.spade.upv.es.pem" if self._traefik_certs else "localhost.pem"
        keyfile = "_wildcard.spade.upv.es-key.pem" if self._traefik_certs else "localhost-key.pem"

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        if not self._enable_tls1_3:
            ssl_context.options |= ssl.OP_NO_TLSv1_3

        ssl_context.load_cert_chain(
            certfile=os.path.join(FILE_AUTH, "..", "..", "certs", certfile),
            keyfile=os.path.join(FILE_AUTH, "..", "..", "certs", keyfile),
        )

        new_transport = await self._loop.start_tls(
            transport=self._transport,
            protocol=self,
            sslcontext=ssl_context,
        )

        self._transport = new_transport
        parser.buffer = self._transport

        logger.debug("Done TLS")
