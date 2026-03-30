import asyncio
from asyncio import Transport
from typing import Union
from xml import sax
from xml.etree.ElementTree import Element
from xml.sax._exceptions import SAXParseException

from loguru import logger

from pyjabber import AppConfig
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.stream.handlers.ServerStanzaHandler import ServerStanzaHandler
from pyjabber.stream.handlers.StanzaHandler import InternalServerError
from pyjabber.stream.negotiators.ServerIncomingStreamNegotiator import ServerIncomingStreamNegotiator


class XMLProtocol(asyncio.Protocol):
    """
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.

    :param namespace: namespace of the XML tags (jabber:client or jabber:server)
    :param connection_timeout: Max time without any response from a client. After that, the protocols will terminate the connection
    """
    __slots__ = ('_xmlns', '_host', '_connection_timeout', '_cert_path', '_connection_manager',
                 '_presence_manager', '_tls_queue', '_transport', '_peer', '_xml_parser',
                 '_timeout_monitor', '_timeout_flag', '_connection_type', '_server_log', '_logger_tag', '_server_incoming')

    def __init__(self, namespace, connection_timeout):
        if namespace not in ["jabber:server", "jabber:client"]:
            raise ValueError('Namespace must be "jabber:server" or "jabber:client')

        self._xmlns = namespace
        self._connection_timeout = connection_timeout

        self._connection_manager = ConnectionManager()
        self._presence_manager = Presence()

        self._transport: Union[Transport, TransportProxy, None] = None
        self._peer = None
        self._xml_parser = None
        self._timeout_monitor = None
        self._timeout_flag = False

        self._server_incoming = namespace == 'jabber:server'

    def __del__(self):
        logger.trace(f"DEBUG: Protocol object for {self._peer or hex(id(self))} has been deleted")

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
        Called when a client or another protocols opens a TCP connection to the protocols

        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        """
        self._peer = transport.get_extra_info('peername')
        logger.info(f"{'Server c' if self._server_incoming else 'C'}onnection from <{self._peer}>")

        if self._connection_timeout:
            self._timeout_monitor = StreamAlivenessMonitor(
                timeout=self._connection_timeout,
                callback=self.connection_timeout
            )

        if AppConfig.app_config.verbose:
            self._transport = TransportProxy(transport, self._peer)
        else:
            self._transport = transport

        self._xml_parser = sax.make_parser()
        self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
        self._xml_parser.setFeature(sax.handler.feature_external_ges, False)

        if self._server_incoming:
            self._xml_parser.setContentHandler(
                XMLParser(
                    self._transport,
                    self,
                    stream_negotiator=ServerIncomingStreamNegotiator,
                    stanza_handler=ServerStanzaHandler
                )
            )

            self._connection_manager.connection_server_incoming(
                self._peer, self._transport
            )
        else:
            self._xml_parser.setContentHandler(
                XMLParser(self._transport, self)
            )

            self._connection_manager.connection(
                self._peer, self._transport
            )



    def connection_lost(self, exc):
        """
        Called when a client or another protocols closes a TCP connection to the protocols

        :param exc: Exception that caused the connection to close
        :type exc: Exception
        """
        if self._timeout_flag:
            return

        logger.info(f"Connection lost <{self._peer}>{f'': Reason {exc}' if exc else ''}")

        self._transport = None
        self._xml_parser.getContentHandler().cancel_queue_bridge()
        self._xml_parser = None
        self._timeout_monitor.cancel()

        if self._server_incoming:
            host = self._connection_manager.get_host(self._peer)
            self._presence_manager.put_nowait(
                (host, Element("presence", attrib={"type": "INTERNAL"}))
            )
            # self._connection_manager.close_server_incoming(self._peer)
        else:
            jid = self._connection_manager.get_jid(self._peer)
            if jid and jid.user and jid.domain:
                self._presence_manager.put_nowait(
                    (jid, Element("presence", attrib={"type": "INTERNAL"}))
                )
            # self._connection_manager.close(self._peer)

        super().connection_lost(None)


    def data_received(self, data):
        """
        Called when data is received from the client or another protocols

        :param data: Chunk of data received
        :type data: Byte array
        """
        try:
            logger.debug(f"Data received {self._peer}: {data.decode()}")
        except UnicodeDecodeError:
            logger.debug(f"Binary data received {self._peer}")

        if self._timeout_monitor:
            self._timeout_monitor.reset()

        # data = data.replace(b"<?xml version=\'1.0\'?>", b"")
        # data = data.replace(b"<?xml version=\"1.0\"?>", b"")

        try:
            self._xml_parser.feed(data)
        except SAXParseException:
            logger.warning(f"<{self._peer}> sent unparsable data")
            self._transport.close()
        except InternalServerError:
            self._transport.close()

    def eof_received(self):
        """
        Called when the client or another protocols sends an EOF
        """
        if self._transport:
            logger.debug(f"EOF {self._peer}")

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
