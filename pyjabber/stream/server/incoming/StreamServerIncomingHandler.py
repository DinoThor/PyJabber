import base64

from typing import Union
from xml.etree import ElementTree as ET

from pyjabber.features.StartTLSFeature import StartTLSFeature, proceed_response
from pyjabber.features.SASLFeature import SASLFeature, MECHANISM
from pyjabber.stream.StreamHandler import StreamHandler, Signal, Stage


class StreamServerIncomingHandler(StreamHandler):
    STARTTLS = "{urn:ietf:params:xml:ns:xmpp-tls}starttls"
    AUTH = "{urn:ietf:params:xml:ns:xmpp-sasl}auth"

    def __init__(self, host, buffer, starttls) -> None:
        super().__init__(host, buffer, starttls)

    def handle_open_stream(self, elem: ET.Element = None) -> Union[Signal, None]:
        if elem is None:
            if self._stage == Stage.CONNECTED:
                self._streamFeature.reset()
                self._streamFeature.register(StartTLSFeature())
                self._buffer.write(self._streamFeature.to_bytes())
                self._stage = Stage.OPENED
                return

            elif self._stage == Stage.SSL:
                self._streamFeature.reset()
                self._streamFeature.register(SASLFeature(mechanismList=[MECHANISM.EXTERNAL]))
                self._buffer.write(self._streamFeature.to_bytes())
                self._stage = Stage.SASL
                return

            elif self._stage == Stage.AUTH:
                self._buffer.write(b"<features xmlns='http://etherx.jabber.org/streams'/>")
                self._stage = Stage.READY
                return Signal.DONE

            else:
                raise Exception()

        elif self._stage == Stage.OPENED and elem.tag == self.STARTTLS:
            self._buffer.write(proceed_response())
            self._starttls()
            self._stage = Stage.SSL
            return Signal.RESET

        elif self._stage == Stage.SASL and elem.tag == self.AUTH:
            if "mechanism" in elem.attrib.keys() and elem.attrib["mechanism"] == "EXTERNAL":
                if elem.text is None:
                    raise Exception()
                elif elem.text == "=":
                    pass
                else:
                    host = base64.b64decode(elem.text).decode()
                    self._buffer.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
                    self._stage = Stage.AUTH
                    return Signal.RESET

        else:
            self._buffer.write(b"<features xmlns='http://etherx.jabber.org/streams'/>")
