from enum import Enum
from typing import Union
from loguru import logger
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.features import InBandRegistration as IBR
from pyjabber.features.StartTLSFeature import StartTLSFeature
from pyjabber.features.StreamFeature import StreamFeature
from pyjabber.features.SASLFeature import SASLFeature, SASL
from pyjabber.features.ResourceBinding import ResourceBinding
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.utils import ClarkNotation as CN


class Stage(Enum):
    """
    Stream connection states.
    """
    CONNECTED   = 0
    OPENED      = 1
    SSL         = 2
    SASL        = 3
    AUTH        = 4
    BIND        = 5
    READY       = 6

class Signal(Enum):
    RESET   = 0
    DONE    = 1

class ServerStreamHandler():
    def __init__(self, buffer, starttls) -> None:
        self._buffer        = buffer
        self._starttls      = starttls

        self._streamFeature = StreamFeature()
        self._connections   = ConnectionManager()
        self._stage         = Stage.CONNECTED

        self._elem          = None
        self._jid           = None

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        self._buffer = value

    def handle_open_stream(self, elem:ET.Element = None) -> Union[Signal, None]:
        # TCP Connection opened
        if self._stage == Stage.CONNECTED:
            self._streamFeature.reset()
            self._streamFeature.register(StartTLSFeature())
            self._buffer.write(self._streamFeature.to_bytes())

            self._stage = Stage.OPENED

        # TLS feature offered
        elif self._stage == Stage.OPENED:
            if "starttls" in elem.tag:
                self._buffer.write(StartTLSFeature().proceed_response())
                self._starttls()
                self._stage = Stage.SSL
                return Signal.RESET

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
                    bindElem    = elem.find(CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind")))
                    resouce     = bindElem.find(CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "resource")))

                    if resouce is not None:
                        resource_id = resouce.text
                    else:
                        resource_id = uuid4()

                    iqRes = ET.Element(
                        "iq",
                        attrib = {
                            "id": elem.attrib["id"],
                            "type": "result"
                        }
                    )

                    bindRes = ET.SubElement(
                        iqRes,
                        "bind",
                        attrib = {
                            "xmlns": "urn:ietf:params:xml:ns:xmpp-bind"
                        }
                    )

                    jidRes      = ET.SubElement(bindRes, "jid")

                    currentJid  = self._connections.get_jid_by_peer(self._buffer.get_extra_info('peername'))
                    jidRes.text = f"{currentJid}@localhost/{resource_id}"

                    self._buffer.write(ET.tostring(iqRes))

                    # Stream is negotiated.
                    # Update the connection register
                    # with the jid and transport
                    self._connections.set_jid(
                        self._buffer.get_extra_info('peername'),
                        jidRes.text, self._buffer
                    )

            return Signal.DONE
