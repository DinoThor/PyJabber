import asyncio
from typing import Union
from xml.etree import ElementTree as ET

from loguru import logger

from pyjabber import AppConfig
from pyjabber.features.Features import SASL_feature, start_tls_proceed_response
from pyjabber.features.SASL.Mechanism import MECHANISM
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.handlers.StanzaHandler import InternalServerError
from pyjabber.stream.negotiators.StreamNegotiator import StreamNegotiator
from pyjabber.stream.utils.Enums import Signal, Stage
from pyjabber.stream.utils.Stream import Stream
from pyjabber.utils import Exceptions as EX
from pyjabber.utils.Exceptions import NotAuthorizerStreamNegotiationException


class ServerIncomingStreamNegotiator(StreamNegotiator):
    def __init__(self, transport, protocol, parser, handler) -> None:
        super().__init__(transport, protocol, parser, handler)
        self._stages_handlers[Stage.AUTH] = self._handle_done_negotiation

    async def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        try:
            if elem.tag == "{http://etherx.jabber.org/streams}stream":
                self._transport.write(Stream.responseStream(elem.attrib))
            return await self._stages_handlers[self._stage](elem)
        except EX.NotAuthorizerStreamNegotiationException:
            self._transport.write(SE.not_authorized())
            self._connection_manager.close_server(self._peer)
        except EX.BadRequestException:
            self._transport.write(SE.bad_request())
            self._connection_manager.close_server(self._peer)
        except InternalServerError:
            self._transport.write(SE.internal_server_error())
            self._connection_manager.close_server(self._peer)
        except Exception as e:
            logger.error(e)

    async def _handle_tls(self, element: ET.Element):
        if element.tag == "{urn:ietf:params:xml:ns:xmpp-tls}starttls":
            self._transport.write(start_tls_proceed_response())
            self._transport.pause_reading()

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
                    sslcontext=AppConfig.app_config.ssl_context,
                    server_side=True,
                )

                if transport_proxy_is_used:
                    new_transport = TransportProxy(new_transport, self._peer)

                self._transport = new_transport
                self._protocol.transport = new_transport
                self._parser.transport = new_transport
                self._handler.transport = new_transport
                self._connection_manager.update_transport_server(
                    new_transport, self._peer
                )

                logger.debug(f"Done TLS for <{self._peer}>")
                self._stage = Stage.SSL
                self._parser.reset_stack()
                self._transport.resume_reading()
                return Signal.RESET

            except ConnectionResetError as e:
                logger.error(
                    f"Error during TLS upgrade with <{self._peer}> Reason: {e}"
                )
                self._connection_manager.close_server(self._peer)
                return Signal.FORCE_CLOSE

        else:
            raise NotAuthorizerStreamNegotiationException()

    async def _handle_init_ssl(self, _):
        self._stream_feature.reset()

        self._stream_feature.register(SASL_feature([MECHANISM.EXTERNAL]))
        self._transport.write(self._stream_feature.to_bytes())

        self._stage = Stage.SASL

    async def _handle_done_negotiation(self):
        return Signal.DONE
