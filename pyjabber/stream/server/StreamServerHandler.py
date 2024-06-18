import ssl
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
from pyjabber.stream.StreamHandler import StreamHandler, Signal, Stage
from pyjabber.utils import ClarkNotation as CN


class StreamServerHandler(StreamHandler):
    def __init__(self, buffer, starttls, connection_manager) -> None:
        super().__init__(buffer, starttls, connection_manager)

    def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        # TCP Connection opened
        if elem.tag == "{http://etherx.jabber.org/streams}features":
            children = [child.tag for child in elem]
            if "{urn:ietf:params:xml:ns:xmpp-tls}starttls" in children:
                if self._stage == Stage.CONNECTED:
                    self._buffer.write("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>".encode())
                    self._stage = Stage.OPENED
                    return

            elif "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms" in children:
                mechanisms = [mech for mech in elem.find("{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")]
                if 'EXTERNAL' in [mech.text for mech in mechanisms]:
                    self._buffer.write("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='EXTERNAL'>=</auth>".encode())

        if elem.tag == "{urn:ietf:params:xml:ns:xmpp-tls}proceed":
            if self._stage == Stage.OPENED:
                self._starttls()
                self._stage = Stage.SSL
                return Signal.RESET

        # if self._stage == Stage.OPENED:https://camo.githubusercontent.com/a5bb0aafd8b664c6279bc394dbe0bf8d19448cfec7c740d884ba11b74f94ab90/68747470733a2f2f696d672e736869656c64732e696f2f707970692f646d2f70796a6162626572
        #     self._streamFeature.reset()
        #     self._streamFeature.register(StartTLSFeature())
        #     self._buffer.write(self._streamFeature.to_bytes())
        #
        #     self._stage = Stage.OPENED
        #
        # # TLS feature offered
        # elif self._stage == Stage.OPENED:
        #     if "starttls" in elem.tag:
        #         self._buffer.write(StartTLSFeature().proceedResponse())
        #         self._starttls()
        #         self._stage = Stage.SSL
        #         return Signal.RESET
        #
        # # TLS Handshake made. Starting SASL
        # elif self._stage == Stage.SSL:
        #     self._streamFeature.reset()
        #
        #     self._streamFeature.register(IBR.InBandRegistration())
        #     self._streamFeature.register(SASLFeature())
        #     self._buffer.write(self._streamFeature.to_bytes())
        #
        #     self._stage = Stage.SASL
        #
        # # SASL
        # elif self._stage == Stage.SASL:
        #     res = SASL().feed(elem, {"peername": self._buffer.get_extra_info('peername')})
        #     if type(res) is tuple:
        #         if res[0].value == Signal.RESET.value:
        #             self._buffer.write(res[1])
        #             self._stage = Stage.AUTH
        #             return Signal.RESET
        #         else:
        #             self._buffer.write(res[1])
        #             self._stage = Stage.AUTH
        #             return
        #
        #     self._buffer.write(res)
        #
        # # User register/authenticated. Starting resource binding
        # elif self._stage == Stage.AUTH:
        #     self._streamFeature.reset()
        #     self._streamFeature.register(ResourceBinding())
        #     self._buffer.write(self._streamFeature.to_bytes())
        #
        #     self._stage = Stage.BIND
        #
        # elif self._stage == Stage.BIND:
        #     if "iq" in elem.tag:
        #         if elem.attrib["type"] == "set":
        #             bindElem = elem.find(CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "bind")))
        #             resouce = bindElem.find(CN.clarkFromTuple(("urn:ietf:params:xml:ns:xmpp-bind", "resource")))
        #
        #             if resouce is not None:
        #                 resource_id = resouce.text
        #             else:
        #                 resource_id = uuid4()
        #
        #             iqRes = ET.Element(
        #                 "iq",
        #                 attrib={
        #                     "id": elem.attrib["id"],
        #                     "type": "result"
        #                 }
        #             )
        #
        #             bindRes = ET.SubElement(
        #                 iqRes,
        #                 "bind",
        #                 attrib={
        #                     "xmlns": "urn:ietf:params:xml:ns:xmpp-bind"
        #                 }
        #             )
        #
        #             jidRes = ET.SubElement(bindRes, "jid")
        #
        #             currentJid = self._connections.get_jid(self._buffer.get_extra_info('peername'))
        #             jidRes.text = f"{currentJid}@localhost/{resource_id}"
        #
        #             self._buffer.write(ET.tostring(iqRes))
        #
        #             # Stream is negotiated.
        #             # Update the connection register
        #             # with the jid and transport
        #             self._connections.set_jid(
        #                 self._buffer.get_extra_info('peername'),
        #                 jidRes.text, self._buffer
        #             )
        #
        #     return Signal.DONE
