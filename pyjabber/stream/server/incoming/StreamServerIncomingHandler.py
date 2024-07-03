import base64
import ssl
from enum import Enum
from typing import Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger

from pyjabber.features import InBandRegistration as IBR
from pyjabber.features.ResourceBinding import ResourceBinding
from pyjabber.features.SASLFeature import SASLFeature, mechanismEnum
from pyjabber.features.StartTLSFeature import StartTLSFeature
from pyjabber.features.StreamFeature import StreamFeature
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.StreamHandler import Signal, Stage, StreamHandler
from pyjabber.utils import ClarkNotation as CN


class StreamServerIncomingHandler(StreamHandler):
    def __init__(self, buffer, starttls, connection_manager) -> None:
        super().__init__(buffer, starttls, connection_manager)

    def handle_open_stream(
            self, elem: ET.Element = None) -> Union[Signal, None]:
        if elem is None:
            if self._stage == Stage.CONNECTED:
                self._streamFeature.reset()
                self._streamFeature.register(StartTLSFeature())
                self._buffer.write(self._streamFeature.to_bytes())
                self._stage = Stage.OPENED
                return

            elif self._stage == Stage.SSL:
                self._streamFeature.reset()
                self._streamFeature.register(SASLFeature(
                    mechanismList=[mechanismEnum.EXTERNAL]))
                self._buffer.write(self._streamFeature.to_bytes())
                self._stage = Stage.SASL
                return

            elif self._stage == Stage.AUTH:
                self._buffer.write(
                    b"<features xmlns='http://etherx.jabber.org/streams'/>")
                self._stage == Stage.READY
                return Signal.DONE

            else:
                raise Exception()

        elif self._stage == Stage.OPENED and elem.tag == "{urn:ietf:params:xml:ns:xmpp-tls}starttls":
            self._buffer.write(StartTLSFeature().proceed_response())
            self._starttls()
            self._stage = Stage.SSL
            return Signal.RESET

        elif self._stage == Stage.SASL and elem.tag == "{urn:ietf:params:xml:ns:xmpp-sasl}auth":
            if "mechanism" in elem.attrib.keys(
            ) and elem.attrib["mechanism"] == "EXTERNAL":
                if elem.text is None:
                    raise Exception()
                elif elem.text == "=":
                    pass
                else:
                    host = base64.b64decode(elem.text).decode()
                    self._buffer.write(
                        b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
                    self._stage = Stage.AUTH
                    return Signal.RESET

        else:
            self._buffer.write(
                b"<features xmlns='http://etherx.jabber.org/streams'/>")

        # elif elem.tag == "{http://etherx.jabber.org/streams}features":
        #     children = [child.tag for child in elem]
        #     if "{urn:ietf:params:xml:ns:xmpp-tls}starttls" in children:
        #         if self._stage == Stage.CONNECTED:
        #             self._buffer.write("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>".encode())
        #             self._stage = Stage.OPENED
        #             return
        #
        #     elif "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms" in children:
        #         mechanisms = [mech for mech in elem.find("{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")]
        #         if 'EXTERNAL' in [mech.text for mech in mechanisms]:
        #             self._buffer.write("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='EXTERNAL'>=</auth>".encode())
        #             return
        #
        #     elif "urn:xmpp:features:dialback{dialback}" in children and self._stage == Stage.READY:
        #         peer = self.buffer.get_extra_info('peername')
        #         self._connections.set_server_transport(peer, self.buffer)
        #         return Signal.DONE
        #
        # elif elem.tag == "{urn:ietf:params:xml:ns:xmpp-tls}proceed":
        #     if self._stage == Stage.OPENED:
        #         self._starttls()
        #         self._stage = Stage.SSL
        #         return Signal.RESET
        #
        # elif elem.tag == "{urn:ietf:params:xml:ns:xmpp-sasl}success":
        #     self._stage = Stage.READY
        #     return Signal.RESET
        #
        # return
