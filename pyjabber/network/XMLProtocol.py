import asyncio
from asyncio import Transport
from typing import Union
from xml import sax
from xml.etree.ElementTree import Element

from loguru import logger

from pyjabber import metadata
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.stream.StanzaHandler import InternalServerError


class XMLProtocol(asyncio.Protocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.

    :param namespace: namespace of the XML tags (jabber:client or jabber:server)
    :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
    """
    __slots__ = ('_xmlns', '_host', '_connection_timeout', '_cert_path', '_connection_manager',
                 '_presence_manager', '_tls_queue', '_transport', '_peer', '_xml_parser',
                 '_timeout_monitor', '_timeout_flag', '_connection_type', '_server_log', '_logger_tag')

    def __init__(self, namespace, connection_timeout):
        self._xmlns = namespace
        self._connection_timeout = connection_timeout

        self._connection_manager = ConnectionManager()
        self._presence_manager = Presence()

        self._transport: Union[Transport, TransportProxy, None] = None
        self._peer = None
        self._xml_parser = None
        self._timeout_monitor = None
        self._timeout_flag = False

        # if self._connection_type == SCT.CLIENT:
        #     self._logger_tag = "from"
        # elif self._connection_type == SCT.FROM_SERVER:
        #     self._logger_tag = "from server"
        # else:
        #     self._logger_tag = "to server"

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, transport: Union[Transport, TransportProxy]):
        self._transport = transport

    @property
    def namespace(self):
        return self._xmlns

    def connection_made(self, transport):
        """
        Called when a client or another server opens a TCP connection to the server

        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        """
        if transport:
            self._peer = transport.get_extra_info('peername')
            logger.info(f"Connection from <{self._peer}>")

            if metadata.VERBOSE:
                self._transport = TransportProxy(transport, self._peer)
            else:
                self._transport = transport

            self._xml_parser = sax.make_parser()
            self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
            self._xml_parser.setFeature(sax.handler.feature_external_ges, False)
            self._xml_parser.setContentHandler(
                XMLParser(self._transport, self)
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection(self._peer, self._transport)
        else:
            logger.error("Invalid transport")

    def connection_lost(self, exc):
        """
        Called when a client or another server closes a TCP connection to the server

        :param exc: Exception that caused the connection to close
        :type exc: Exception
        """
        if self._timeout_flag:
            return

        logger.info(f"Connection lost {self._logger_tag} {self._peer}: Reason {exc}")

        jid = self._connection_manager.get_jid(self._peer)
        if jid and jid.user and jid.domain:
            self._presence_manager.feed(
                jid, Element("presence", attrib={"type": "INTERNAL"})
            )

        self._transport = None
        self._xml_parser = None
        self._timeout_monitor.cancel()

        self._connection_manager.disconnection(self._peer)

    def data_received(self, data):
        """
        Called when data is received from the client or another server

        :param data: Chunk of data received
        :type data: Byte array
        """
        logger.debug(f"Data received {self._peer}: {data.decode(errors='ignore')}")

        if self._timeout_monitor:
            self._timeout_monitor.reset()

        data = data.replace(b"<?xml version=\'1.0\'?>", b"")
        data = data.replace(b"<?xml version=\"1.0\"?>", b"")

        try:
            self._xml_parser.feed(data)
        except InternalServerError:
            self._transport.close()

    def eof_received(self):
        """
        Called when the client or another server sends an EOF
        """
        if self._transport:
            logger.debug(f"EOF {self._logger_tag} {self._peer}")

    def connection_timeout(self):
        """
        Called when the stream is not responding for a long time
        """
        if not self._transport:
            return

        logger.info(f"Connection timeout {self._logger_tag} {self._peer}")
        if not self._transport.is_closing():
            self._transport.write("<connection-timeout/>".encode())
            self._transport.close()
