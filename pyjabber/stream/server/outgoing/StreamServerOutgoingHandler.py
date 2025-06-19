from typing import Union
from xml.etree import ElementTree as ET

from pyjabber.stream.StreamHandler import Signal, Stage, StreamHandler


class StreamServerOutgoingHandler(StreamHandler):

    PROCEED = "{urn:ietf:params:xml:ns:xmpp-tls}proceed"
    SUCCESS = "{urn:ietf:params:xml:ns:xmpp-sasl}success"
    DIALBACK = "urn:xmpp:features:dialback{dialback}"
    MECHANISMS = "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms"
    FEATURES = "{http://etherx.jabber.org/streams}features"
    STARTTLS = "{urn:ietf:params:xml:ns:xmpp-tls}starttls"

    def __init__(self, buffer, starttls) -> None:
        super().__init__(buffer, starttls)

    def handle_open_stream(
            self, elem: ET.Element = None) -> Union[Signal, None]:
        if self._stage == Stage.READY:
            return Signal.DONE

        elif elem.tag == self.FEATURES:
            children = [child.tag for child in elem]
            if self.STARTTLS in children:
                if self._stage == Stage.CONNECTED:
                    self._transport.write(
                        "<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>".encode())
                    self._stage = Stage.OPENED
                    return

            elif self.MECHANISMS in children:
                mechanisms = [mech for mech in elem.find(self.MECHANISMS)]
                if 'EXTERNAL' in [mech.text for mech in mechanisms]:
                    self._transport.write(
                        "<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='EXTERNAL'>=</auth>".encode())
                    return

            else:
                peer = self._transport.get_extra_info('peername')
                return Signal.DONE

        elif elem.tag == self.PROCEED:
            if self._stage == Stage.OPENED:
                self._starttls()
                self._stage = Stage.SSL
                return Signal.CLEAR

        elif elem.tag == self.SUCCESS:
            self._stage = Stage.READY
            return Signal.RESET

        return
