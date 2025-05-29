import asyncio
import os
from asyncio import Transport
from typing import Union

from loguru import logger
from xml import sax
from xml.etree.ElementTree import Element

from pyjabber import metadata
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.ServerConnectionType import ServerConnectionType as SCT
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.network.parsers.XMLServerIncomingParser import XMLServerIncomingParser
from pyjabber.network.parsers.XMLServerOutcomingParser import XMLServerOutcomingParser
from pyjabber.stream.StanzaHandler import InternalServerError

FILE_AUTH = os.path.dirname(os.path.abspath(__file__))


class TransportProxy:
    def __init__(self, transport, peer):
        self._transport = transport
        self._peer = peer

    @property
    def originalTransport(self):
        return self._transport

    def write(self, data):
        logger.trace(f"Sending to {'server' if self.from_to_server else ''} {self._peer}: {data}")
        return self._transport.write(data)

    def __getattr__(self, name):
        return getattr(self._transport, name)


class XMLProtocol(asyncio.Protocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.

    :param namespace: namespace of the XML tags (jabber:client or jabber:server)
    :param host: Host for connections
    :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
    :param cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname
    """
    def __init__(
            self,
            namespace,
            host,
            connection_timeout,
            cert_path,
            connection_type):

        self._xmlns = namespace
        self._host = host
        self._connection_timeout = connection_timeout
        self._connection_manager = ConnectionManager()
        self._presence_manager = Presence()
        self._cert_path = cert_path
        self._tls_queue = metadata.TLS_QUEUE

        self._transport = None
        self._peer = None
        self._xml_parser = None
        self._timeout_monitor = None
        self._timeout_flag = False

        self._connection_type = connection_type or SCT.CLIENT
        self._server_log = self._connection_type != SCT.CLIENT

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, transport: Union[Transport, TransportProxy]):
        self._transport = transport

    def connection_made(self, transport):
        """
        Called when a client or another server opens a TCP connection to the server

        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        """
        if transport:
            self._peer = transport.get_extra_info('peername')
            self._transport = TransportProxy(transport, self._peer)

            self._xml_parser = sax.make_parser()
            self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
            self._xml_parser.setFeature(sax.handler.feature_external_ges, False)
            if self._connection_type == SCT.FROM_SERVER:
                self._xml_parser.setContentHandler(
                    XMLServerIncomingParser(self._transport, self.task_tls)
                )
            elif self._connection_type == SCT.TO_SERVER:
                self._xml_parser.setContentHandler(
                    XMLServerOutcomingParser(self._transport, self.task_tls)
                )
            else:
                self._xml_parser.setContentHandler(
                    XMLParser(self._transport, self.task_tls)
                )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            if self._connection_type == SCT.CLIENT:
                self._connection_manager.connection(self._peer, self._transport)
            else:
                self._connection_manager.connection_server(self._peer, self._transport)

            logger.info(f"Connection from {self._peer}")
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

        logger.info(f"Connection lost from {'server' if self._server_log else ''} {self._peer}: Reason {exc}")
        if self._connection_type == SCT.CLIENT:
            jid = self._connection_manager.get_jid(self._peer)
            if jid and jid.user and jid.domain:
                self._presence_manager.feed(jid, Element("presence", attrib={"type": "INTERNAL"}))
        self._transport = None
        self._xml_parser = None
        self._timeout_monitor.cancel()

        if self._connection_type == SCT.CLIENT:
            self._connection_manager.disconnection(self._peer)
        else:
            self._connection_manager.disconnection_server(self._peer)

    def data_received(self, data):
        """
        Called when data is received from the client or another server

        :param data: Chunk of data received
        :type data: Byte array
        """
        logger.debug(f"Data received from <{self._peer}>: {data.decode()}")

        if self._timeout_monitor:
            self._timeout_monitor.reset()

        data = data.replace(b"<?xml version=\'1.0\'?>", b"")
        data = data.replace(b"<?xml version=\"1.0\"?>", b"")

        try:
            self._xml_parser.feed(data)
        except InternalServerError:
            pass  # TODO: handle exception

    def eof_received(self):
        """
        Called when the client or another server sends an EOF
        """
        if self._transport:
            logger.debug(f"EOF received from {'server' if self._server_log else ''}{self._peer}")

    def connection_timeout(self):
        """
        Called when the stream is not responding for a long tikem
        """
        logger.info(f"Connection timeout from {'server' if self._server_log else ''}{self._peer}")

        try:
            self._transport.write("<connection-timeout/>".encode())
            self._transport.close()
        except:
            logger.warning(f"Connection with {'server' if self._server_log else ''} {self._peer} is already closed. Removing from online list")

        if self._connection_type == SCT.CLIENT:
            self._connection_manager.disconnection(self._peer)
        else:
            self._connection_manager.disconnection_server(self._peer)

        self._transport = None
        self._xml_parser = None
        self._timeout_flag = True

    def task_tls(self):
        """
            Sync function to call the STARTTLS coroutine
        """
        self._tls_queue.put_nowait((self._transport, self, self._xml_parser.getContentHandler()))
