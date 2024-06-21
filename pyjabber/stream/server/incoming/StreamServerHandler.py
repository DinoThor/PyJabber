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
        if self._stage == Stage.READY:
            peer = self.buffer.get_extra_info('peername')
            self._connections.set_server_transport(peer, self.buffer)
            return Signal.DONE

        elif elem.tag == "{http://etherx.jabber.org/streams}features":
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
                    return

        elif elem.tag == "{urn:ietf:params:xml:ns:xmpp-tls}proceed":
            if self._stage == Stage.OPENED:
                self._starttls()
                self._stage = Stage.SSL
                return Signal.RESET

        elif elem.tag == "{urn:ietf:params:xml:ns:xmpp-sasl}success":
            self._stage = Stage.READY
            return Signal.RESET

        return
