import asyncio
import ssl
import os

from loguru import logger
from xml import sax

from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor
from pyjabber.network.XMLParser import XMPPStreamHandler
from pyjabber.network.ConnectionsManager import ConectionsManager



class XMLProtocol(asyncio.Protocol):
    '''
    Protocol to manage the network connection between nodes in the XMPP network. Handles the transport layer.
    '''

    __slots__ = [
        "_transport", 
        "_xmlns", 
        "_xml_parser", 
        "_connection_timeout", 
        "_timeout_monitor",
        "_connections"
    ]

    def __init__(
            self, 
            namespace                       = "jabber:client", 
            connection_timeout              = None):
        
        self._xmlns                 = namespace
        self._transport             = None
        self._xml_parser            = None
        self._timeout_monitor       = None
        self._connection_timeout    = connection_timeout
        self._connections           = ConectionsManager()


    def connection_made(self, transport):
        '''
        Called when a client or another server opens a TCP connection to the server
        
        :param transport: The transport object for the connection
        :type transport: asyncio.Transport
        '''
        if transport:
            self._transport = transport

            self._xml_parser = sax.make_parser()
            self._xml_parser.setFeature(sax.handler.feature_namespaces, True)
            self._xml_parser.setFeature(sax.handler.feature_external_ges, False)
            self._xml_parser.setContentHandler(
                XMPPStreamHandler(self._transport, self.taskTLS)
            )

            if self._connection_timeout:
                self._timeout_monitor = StreamAlivenessMonitor(
                    timeout     = self._connection_timeout, 
                    callback    = self.connection_timeout
                )

            self._connections.connection(self._transport.get_extra_info('peername'))

            logger.info(f"Connection from {self._transport.get_extra_info('peername')}")
        else:
            self._transport = None
            self._xml_parser = None

            logger.error("Invalid transport")

    def connection_lost(self, exc):
        '''
        Called when a client or another server closes a TCP connection to the server

        :param exc: Exception that caused the connection to close
        :type exc: Exception
        '''
        try:
            logger.info(f"Connection lost from {self._transport.get_extra_info('peername')}: Reason {exc}")
            self._transport     = None
            self._xml_parser    = None

        except:
            logger.info(f"Connection lost after EOF recived")


    def data_received(self, data):
        '''
        Called when data is received from the client or another server

        :param data: Chunk of data received
        :type data: Byte array
        '''
        try:
            logger.debug(f"Data received: {data.decode()}")
        except:
            return

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
        data = data.replace(b"<?xml version=\"1.0\"?>", b"")
        # try:
        self._xml_parser.feed(data)
        # except sax.SAXParseException as e:
        #     logger.error(f"Error parsing XML: {e}")
        # except Exception as e:
        #     logger.error(f"Error parsing XML: {e}")


    def eof_received(self):
        '''
        Called when the client or another server sends an EOF
        '''
        peer = self._transport.get_extra_info('peername')

        logger.debug(f"EOF received from {peer}")

        self._connections.disconnection(peer)

        self._transport     = None
        self._xml_parser    = None

    def connection_timeout(self):
        '''
        Called when the stream is not responding for a long tikem
        '''
        logger.debug(f"Connection timeout from {self._transport.get_extra_info('peername')}")

        self._transport.write("<connection-timeout/>".encode())
        self._transport.close()

        self._transport     = None
        self._xml_parser    = None

    def taskTLS(self):
        task = asyncio.get_running_loop().create_task(self.enableTLS())
        task.add_done_callback(self.handleSTARTTLS)

    async def enableTLS(self):
        print(os.getcwd() + 'pyjabber/network/certs/localhost.pem')
        loop        = asyncio.get_running_loop()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(
            os.getcwd() + '/pyjabber/network/certs/localhost.pem',     # Cert file
            os.getcwd() + '/pyjabber/network/certs/localhost-key.pem') # Key file

        return await loop.start_tls(
                                transport   = self._transport, 
                                protocol    = self._transport.get_protocol(), 
                                sslcontext  = ssl_context,
                                server_side = True)
    
    def handleSTARTTLS(self, task):
        new_transport   = task.result()
        self._transport = new_transport
        parser          = self._xml_parser.getContentHandler()
        parser.buffer   = new_transport
        logger.debug("Done TLS")

