import os
from xml import sax

from loguru import logger

from pyjabber.network.server.incoming.XMLServerIncomingParser import (
    XMLServerIncomingParser,
)
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLProtocol import XMLProtocol

FILE_AUTH = os.path.dirname(os.path.abspath(__file__))


class XMLServerIncomingProtocol(XMLProtocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.
    """

    def __init__(
            self,
            namespace,
            host,
            connection_timeout,
            cert_path):

        super().__init__(
            namespace,
            host,
            connection_timeout,
            cert_path)

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
                XMLServerIncomingParser(
                    self._host,
                    self._transport,
                    self.task_tls
                )
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection(
                self._transport.get_extra_info('peername'))

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
