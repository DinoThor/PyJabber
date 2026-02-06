import asyncio
from typing import Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger

from pyjabber.AppConfig import AppConfig
from pyjabber.features.Features import (
    SASL_feature,
    in_band_registration_feature,
    resource_binding_feature,
    start_tls_feature,
    start_tls_proceed_response,
)
from pyjabber.features.SASL.SASL import SASL
from pyjabber.features.StreamFeature import StreamFeature
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.utils.Enums import Stage, Signal
from pyjabber.stream.StanzaHandler import InternalServerError
from pyjabber.stream.Stream import Stream
from pyjabber.utils import Exceptions as EX
from pyjabber.utils.Exceptions import NotAuthorizerStreamNegotiationException


class StreamHandler:
    def __init__(self, transport, protocol, parser) -> None:
        self._host = AppConfig.host

        self._transport = transport
        self._peer = transport.get_extra_info("peername")
        self._protocol = protocol
        self._parser = parser
        self._ssl_context = AppConfig.ssl_context

        self._streamFeature = StreamFeature()
        self._connection_manager: ConnectionManager = ConnectionManager()
        self._stage = Stage.CONNECTED

        self._ibr_feature = 'jabber:iq:register' in AppConfig.plugins

        self._sasl = None

        self._stages_handlers = {
            Stage.CONNECTED: self._handle_init,
            Stage.OPENED: self._handle_tls,
            Stage.SSL: self._handle_init_ssl,
            Stage.SASL: self._handle_ssl,
            Stage.AUTH: self._handle_init_resource_bind,
            Stage.BIND: self._handle_resource_bind
        }

    async def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        try:
            if elem.tag == '{http://etherx.jabber.org/streams}stream':
                self._transport.write(Stream.responseStream(elem.attrib))
            return await self._stages_handlers[self._stage](elem)
        except EX.NotAuthorizerStreamNegotiationException:
            self._transport.write(SE.not_authorized())
            self._connection_manager.close(self._peer)
        except EX.BadRequestException:
            self._transport.write(SE.bad_request())
            self._connection_manager.close(self._peer)
        except InternalServerError:
            self._transport.write(SE.internal_server_error())
            self._connection_manager.close(self._peer)
        except Exception as e:
            logger.error(e)

    async def _handle_init(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(start_tls_feature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.OPENED

    async def _handle_tls(self, element: ET.Element):
        if element.tag == "{urn:ietf:params:xml:ns:xmpp-tls}starttls":
            self._transport.write(start_tls_proceed_response())
            self._transport.pause_reading()

            if isinstance(self._transport, TransportProxy):
                original_transport = self._transport.original_transport
            else:
                original_transport = self._transport

            try:
                loop = asyncio.get_running_loop()
                new_transport = await loop.start_tls(
                    transport=original_transport,
                    protocol=self._protocol,
                    sslcontext=self._ssl_context,
                    server_side=True
                )

                new_transport = TransportProxy(new_transport, self._peer)
                self._transport = new_transport
                self._protocol.transport = new_transport
                self._parser.transport = new_transport
                self._connection_manager.update_buffer(new_transport=new_transport, peer=self._peer)

                logger.debug(f"Done TLS for <{self._peer}>")
                self._stage = Stage.SSL
                self._parser.reset_stack()
                self._transport.resume_reading()
                return Signal.RESET

            except ConnectionResetError:
                logger.error(f"Error during TLS upgrade with <{self._peer}>")
                self._connection_manager.close(self._peer)
                return Signal.FORCE_CLOSE

        else:
            raise NotAuthorizerStreamNegotiationException()

    async def _handle_init_ssl(self, _):
        self._streamFeature.reset()

        if self._ibr_feature:
            self._streamFeature.register(in_band_registration_feature())

        self._streamFeature.register(SASL_feature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.SASL

    async def _handle_ssl(self, element: ET.Element):
        if self._sasl is None:
            self._sasl = SASL(self._transport, self._parser, self._peer)

        res = await self._sasl.feed(element)

        if res and res == Stage.AUTH:
            self._stage = Stage.AUTH

    async def _handle_init_resource_bind(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(resource_binding_feature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.BIND

    async def _handle_resource_bind(self, element: ET.Element):
        if (element.tag == "{jabber:client}iq"
            and len(element) > 0
            and element[0].tag == "{urn:ietf:params:xml:ns:xmpp-bind}bind"
            and element.attrib.get("type") == "set"):

                resource_id = str(uuid4())

                iq_res = IQ(type_=IQ.TYPE.RESULT, id_=element.get('id') or str(uuid4()))
                bind_res = ET.SubElement(iq_res, "bind", attrib={"xmlns": "urn:ietf:params:xml:ns:xmpp-bind"})

                peername = self._transport.get_extra_info('peername')
                new_jid = self._connection_manager.get_jid(peername)
                new_jid.resource = resource_id

                ET.SubElement(bind_res, 'jid').text = str(new_jid)
                self._transport.write(ET.tostring(iq_res))

                self._connection_manager.set_jid(peername, new_jid, self._transport)
                return Signal.DONE

        else:
            raise NotAuthorizerStreamNegotiationException()
