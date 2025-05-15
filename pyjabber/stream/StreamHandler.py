from asyncio import Transport
from enum import Enum
from typing import Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.features import InBandRegistration as IBR
from pyjabber.features.StartTLSFeature import StartTLSFeature, proceed_response
from pyjabber.features.StreamFeature import StreamFeature
from pyjabber.features.SASLFeature import SASLFeature, SASL
from pyjabber.features.ResourceBinding import ResourceBinding
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber import metadata
from pyjabber.stanzas.IQ import IQ
from pyjabber.stanzas.error import StanzaError as SE

class Stage(Enum):
    """
    Stream connection states.
    """
    CONNECTED = 0
    OPENED = 1
    SSL = 2
    SASL = 3
    AUTH = 4
    BIND = 5
    READY = 6


class Signal(Enum):
    RESET = 0
    DONE = 1
    FORCE_CLOSE = 2

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return self.value == other.value


class StreamHandler:
    def __init__(self, transport, starttls) -> None:
        self._host = metadata.HOST
        self._transport = transport
        self._starttls = starttls
        self._streamFeature = StreamFeature()
        self._connection_manager: ConnectionManager = ConnectionManager()
        self._stage = Stage.CONNECTED

        self._stages_handlers = {
            Stage.CONNECTED: self._handle_init,
            Stage.OPENED: self._handle_tls,
            Stage.SSL: self._handle_init_ssl,
            Stage.SASL: self._handle_ssl,
            Stage.AUTH: self._handle_init_resource_bind,
            Stage.BIND: self._handle_resource_bind
        }

    @property
    def transport(self) -> Transport:
        return self._transport

    @transport.setter
    def transport(self, transport: Transport):
        self._transport = transport

    def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        try:
            return self._stages_handlers[self._stage](elem)
        except KeyError:
            SE.internal_server_error()

    def _handle_init(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(StartTLSFeature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.OPENED

    def _handle_tls(self, element: ET.Element):
        if "starttls" in element.tag:
            self._transport.write(proceed_response())
            self._starttls()
            self._stage = Stage.SSL
            self._transport.pause_reading()
            return Signal.RESET

        else:
            raise Exception()

    def _handle_init_ssl(self, _):
        self._streamFeature.reset()

        self._streamFeature.register(IBR.InBandRegistration())
        self._streamFeature.register(SASLFeature())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.SASL

    def _handle_ssl(self, element: ET.Element):
        res = SASL().feed(element, {"peername": self._transport.get_extra_info('peername')})
        if type(res) is tuple:
            if res[0].value == Signal.RESET.value:
                self._transport.write(res[1])
                self._stage = Stage.AUTH
                return Signal.RESET
            else:
                self._transport.write(res[1])
                self._stage = Stage.AUTH
                return

        self._transport.write(res)

    def _handle_init_resource_bind(self, _):
        self._streamFeature.reset()
        self._streamFeature.register(ResourceBinding())
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.BIND

    def _handle_resource_bind(self, element: ET.Element):
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

