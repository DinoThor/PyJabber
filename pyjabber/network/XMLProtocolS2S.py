from xml import sax

from loguru import logger

from pyjabber.AppConfig import AppConfig
from pyjabber.network.parsers.XMLServerIncomingParser import XMLServerIncomingParser
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.network.XMLProtocol import XMLProtocol


class XMLProtocolS2S(XMLProtocol):
    def __init__(self, namespace, host, connection_timeout):
        super().__init__(namespace, connection_timeout)
        self._host = host

    def connection_made(self, transport):
        """
        Called when a client or another server opens a TCP connection to the server

        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        """
        if transport:
            self._peer = transport.get_extra_info('peername')
            logger.info(f"Connection {self._logger_tag} {self._peer}")

            if AppConfig.verbose:
                self._transport = TransportProxy(transport, self._peer)
            else:
                self._transport = transport

            self._xml_parser = sax.make_parser()
            self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
            self._xml_parser.setFeature(sax.handler.feature_external_ges, False)
            self._xml_parser.setContentHandler(
                XMLServerIncomingParser(self._transport, self)
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection_server(
                self._peer, self._transport, self._host
            )
        else:
            logger.error("Invalid transport")

    def connection_lost(self, exc):
        """
        Called when a server closes a TCP connection to the server

        :param exc: Exception that caused the connection to close
        :type exc: Exception
        """
        if self._timeout_flag:
            return

        logger.info(f"Connection lost {self._logger_tag} {self._peer}: Reason {exc}")

        self._transport = None
        self._xml_parser = None
        self._timeout_monitor.cancel()

        self._connection_manager.disconnection_server(self._peer)
