import asyncio
from asyncio import Transport
from typing import Union, List
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.features import InBandRegistration as IBR
from pyjabber.features.StartTLSFeature import StartTLSFeature, proceed_response
from pyjabber.features.StreamFeature import StreamFeature
from pyjabber.features.SASLFeature import SASLFeature, SASL, MECHANISM
from pyjabber.features.ResourceBinding import ResourceBinding
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber import metadata
from pyjabber.stanzas.IQ import IQ
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.Stage import Stage
from pyjabber.stream.Signal import Signal

from loguru import logger

from pyjabber.stream.Stream import Stream
from pyjabber.utils.TransportProxy import TransportProxy


class StreamHandler:
    def __init__(self, transport, protocol, parser) -> None:
        self._host = metadata.HOST

        self._transport = transport
        self._protocol = protocol
        self._parser = parser
        self._ssl_context = metadata.SSL_CONTEXT

        self._streamFeature = StreamFeature()
        self._connection_manager: ConnectionManager = ConnectionManager()
        self._stage = Stage.CONNECTED

        self._ibr_feature = 'jabber:iq:register' in metadata.PLUGINS

        self._sasl = None
        self._sasl_mechanisms: List[MECHANISM] = []

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
        except Exception:
            SE.internal_server_error()

    async def _handle_init(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(StartTLSFeature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.OPENED
        return

    async def _handle_tls(self, element: ET.Element):
        if "starttls" in element.tag:
            self._transport.write(proceed_response())
            self._transport.pause_reading()

            peer = self._transport.get_extra_info("peername")
            try:
                new_transport = await asyncio.get_running_loop().start_tls(
                    transport=self._transport.originalTransport,
                    protocol=self._protocol,
                    sslcontext=self._ssl_context,
                    server_side=True
                )

                new_transport = TransportProxy(new_transport, peer)
                self._transport = new_transport
                self._protocol.transport = new_transport
                self._parser.transport = new_transport
                if self._protocol.namespace == 'jabber:client':
                    self._connection_manager.update_buffer(new_transport=new_transport, peer=peer)
                else:
                    self._connection_manager.update_transport_server(new_transport=new_transport, peer=peer)

                logger.debug(f"Done TLS for <{peer}>")
                self._stage = Stage.SSL
                self._parser.reset_stack()
                self._transport.resume_reading()
                return Signal.RESET

            except ConnectionResetError as e:
                logger.error(f"ERROR DURING TLS UPGRADE WITH <{peer}>")
                self._connection_manager.close(peer)
                return Signal.FORCE_CLOSE

        else:
            raise Exception()

    async def _handle_init_ssl(self, _):
        self._streamFeature.reset()

        if self._ibr_feature:
            self._streamFeature.register(IBR.InBandRegistration())
        self._streamFeature.register(SASLFeature(mechanism_list=self._sasl_mechanisms))
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.SASL

    async def _handle_ssl(self, element: ET.Element):
        if self._sasl is None:
            self._sasl = SASL(self._transport, self._parser)

        res = await self._sasl.feed(
            element, self._transport, self._transport.get_extra_info('peername')
        )

        if res and res == Stage.AUTH:
            self._stage = Stage.AUTH

    async def _handle_init_resource_bind(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(ResourceBinding())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.BIND

    async def _handle_resource_bind(self, element: ET.Element):
        if "iq" in element.tag:
            if element.attrib.get("type") == "set":
                resource_id = str(uuid4())

                iq_res = IQ(type_=IQ.TYPE.RESULT, id_=element.get('id') or str(uuid4()))
                bind_res = ET.SubElement(iq_res, "bind", attrib={"xmlns": "urn:ietf:params:xml:ns:xmpp-bind"})

                peername = self._transport.get_extra_info('peername')
                new_jid = self._connection_manager.get_jid(peername)
                new_jid.resource = resource_id

                ET.SubElement(bind_res, 'jid').text = str(new_jid)

                self._transport.write(ET.tostring(iq_res))

                """
                Stream is negotiated.
                Update the connection register with the jid and transport
                """
                self._connection_manager.set_jid(peername, new_jid, self._transport)

        return Signal.DONE
