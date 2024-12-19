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
from pyjabber.metadata import host
from pyjabber.stanzas.IQ import IQ


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

    def __eq__(self, other):
        if other is None:
            return False
        return self.value == other.value


class StreamHandler:
    def __init__(self, buffer, starttls) -> None: # connection_manager
        self._host = host.get()
        self._buffer = buffer
        self._starttls = starttls

        self._streamFeature = StreamFeature()
        self._connection_manager: ConnectionManager = ConnectionManager()
        self._stage = Stage.CONNECTED

        self._elem = None
        self._jid = None

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        self._buffer = value

    def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        # TCP Connection opened
        if self._stage == Stage.CONNECTED:
            self._streamFeature.reset()
            self._streamFeature.register(StartTLSFeature())
            self._buffer.write(self._streamFeature.to_bytes())

            self._stage = Stage.OPENED
            return

        # TLS feature offered
        elif self._stage == Stage.OPENED:
            if "starttls" in elem.tag:
                self._buffer.write(proceed_response())
                self._starttls()
                self._stage = Stage.SSL
                return Signal.RESET

            else:
                raise Exception()

        # TLS Handshake made. Starting SASL
        elif self._stage == Stage.SSL:
            self._streamFeature.reset()

            self._streamFeature.register(IBR.InBandRegistration())
            self._streamFeature.register(SASLFeature())
            self._buffer.write(self._streamFeature.to_bytes())

            self._stage = Stage.SASL

        # SASL
        elif self._stage == Stage.SASL:
            res = SASL().feed(elem, {"peername": self._buffer.get_extra_info('peername')})
            if type(res) is tuple:
                if res[0].value == Signal.RESET.value:
                    self._buffer.write(res[1])
                    self._stage = Stage.AUTH
                    return Signal.RESET
                else:
                    self._buffer.write(res[1])
                    self._stage = Stage.AUTH
                    return

            self._buffer.write(res)

        # User register/authenticated. Starting resource binding
        elif self._stage == Stage.AUTH:
            self._streamFeature.reset()
            self._streamFeature.register(ResourceBinding())
            self._buffer.write(self._streamFeature.to_bytes())

            self._stage = Stage.BIND

        elif self._stage == Stage.BIND:
            if "iq" in elem.tag:
                if elem.attrib["type"] == "set":
                    resource_id = str(uuid4())

                    iq_res = IQ(type_=IQ.TYPE.RESULT, id_=elem.get('id') or str(uuid4()))
                    bind_res = ET.SubElement(iq_res, "bind", attrib={"xmlns": "urn:ietf:params:xml:ns:xmpp-bind"})

                    peername = self._buffer.get_extra_info('peername')
                    new_jid = self._connection_manager.get_jid(peername)
                    new_jid.resource = resource_id

                    ET.SubElement(bind_res, 'jid').text = str(new_jid)

                    self._buffer.write(ET.tostring(iq_res))

                    """
                    Stream is negotiated.
                    Update the connection register with the jid and transport
                    """
                    self._connection_manager.set_jid(peername, new_jid, self._buffer)

            return Signal.DONE
