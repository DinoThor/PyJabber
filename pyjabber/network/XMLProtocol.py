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
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLParser import XMLParser
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
        logger.trace(f"Sending to {self._peer}: {data}")
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
            cert_path):

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
            self._xml_parser.setContentHandler(
                XMLParser(self._transport, self.task_tls)
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout=self._connection_timeout,
                    callback=self.connection_timeout
                )

            self._connection_manager.connection(self._peer, self._transport)

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

        logger.info(f"Connection lost from {self._peer}: Reason {exc}")
        jid = self._connection_manager.get_jid(self._peer)
        if jid and jid.user and jid.domain:
            self._presence_manager.feed(jid, Element("presence", attrib={"type": "INTERNAL"}))

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
        try:
            logger.debug(f"Data received from <{self._peer}>: {data.decode()}")
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

        try:
            self._xml_parser.feed(data)
        except InternalServerError:
            a = 1
            pass

    def eof_received(self):
        """
        Called when the client or another server sends an EOF
        """
        if self._transport:
            logger.debug(f"EOF received from {self._peer}")

    def connection_timeout(self):
        """
        Called when the stream is not responding for a long tikem
        """
        logger.info(f"Connection timeout from {self._peer}")

        try:
            self._transport.write("<connection-timeout/>".encode())
            self._transport.close()
        except:
            logger.warning(f"Connection with {self._peer} is already closed. Removing from online list")

        self._connection_manager.disconnection(self._peer)

        self._transport = None
        self._xml_parser = None
        self._timeout_flag = True

    def task_tls(self):
        """
            Sync function to call the STARTTLS coroutine
        """
        self._tls_queue.put_nowait((self._transport, self, self._xml_parser.getContentHandler()))
