import asyncio
from typing import Union
from xml.etree import ElementTree as ET

from loguru import logger

from pyjabber import AppConfig
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.QueueManager import get_queue, QueueName
from pyjabber.stream.negotiators.StreamNegotiator import Signal, Stage, StreamNegotiator


class StreamServerNegotiator(StreamNegotiator):
    def __init__(self, transport, protocol, parser, handler) -> None:
        super().__init__(transport, protocol, parser, handler)

        self._connection_queue = get_queue(QueueName.CONNECTIONS)

        self._stages_handlers = {
            Stage.CONNECTED: self._handle_init,
            Stage.OPENED: self._handle_tls,
            Stage.SSL: self._handle_init_ssl,
            Stage.SASL: self._handle_ssl,
            Stage.AUTH: self._handle_init_resource_bind,
            Stage.BIND: self._handle_resource_bind
        }

        self._stages_flags = {
            "starttls": False,
            "starttls_handshake": False,
            "auth": False,
        }

    async def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        if elem.tag == "{http://etherx.jabber.org/streams}features":
            children = [child.tag for child in elem]
            if ("{urn:ietf:params:xml:ns:xmpp-tls}starttls" in children
                and self._stages_flags["starttls"] is False):
                    self._transport.write("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>".encode())
                    self._stages_flags["starttls"] = True

            elif ("{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms" in children
                  and self._stages_flags["starttls"]
                  and self._stages_flags["starttls_handshake"]):

                mechanisms_offered = [m for m in elem.find("{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")]
                if any('EXTERNAL' == m.text for m in mechanisms_offered):
                    self._transport.write(
                        "<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='EXTERNAL'>=</auth>".encode())

        elif (elem.tag == "{urn:ietf:params:xml:ns:xmpp-tls}proceed"
              and self._stages_flags["starttls"]
              and self._stages_flags["starttls_handshake"] is False):

                await self.handle_tls_server()
                self._parser.reset_stack()
                self._stages_flags["starttls_handshake"] = True

        elif elem.tag == "{urn:ietf:params:xml:ns:xmpp-sasl}success":
            self._stages_flags["auth"] = True

        if all(self._stages_flags.values()):
            self._parser.reset_stack()
            return Signal.DONE
        else:
            return None

    async def handle_tls_server(self):
        transport_proxy_is_used = isinstance(self._transport, TransportProxy)
        if transport_proxy_is_used:
            original_transport = self._transport.original_transport
        else:
            original_transport = self._transport

        try:
            loop = asyncio.get_running_loop()
            new_transport = await loop.start_tls(
                transport=original_transport,
                protocol=self._protocol,
                sslcontext=AppConfig.app_config.ssl_context_s2s,
            )

            if transport_proxy_is_used:
                new_transport = TransportProxy(new_transport, self._peer)

            self._transport = new_transport
            self._protocol.transport = new_transport
            self._parser.transport = new_transport
            self._handler.transport = new_transport
            self._connection_manager.update_transport_server(new_transport, self._peer)

            logger.debug(f"Done TLS for <{self._peer}>")
        except ConnectionResetError as e:
            logger.error(f"Error during TLS upgrade with <{self._peer}> Reason: {e}")
            self._connection_manager.close(self._peer)
            return Signal.FORCE_CLOSE
