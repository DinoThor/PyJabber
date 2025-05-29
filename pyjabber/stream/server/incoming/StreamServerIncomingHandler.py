from typing import List
from xml.etree import ElementTree as ET

from pyjabber import metadata
from pyjabber.features.SASLFeature import MECHANISM
from pyjabber.stream.StreamHandler import StreamHandler, Signal, Stage
from pyjabber.stanzas.error import StanzaError as SE

try:
    from typing import override
except ImportError:
    def override(func): return func


class StreamServerIncomingHandler(StreamHandler):
    sasl_mechanisms: List[MECHANISM] = [MECHANISM.EXTERNAL]
    ibr_feature: bool = False

    def __init__(self, transport, starttls) -> None:
        super().__init__(transport, starttls)

    @override
    def _handle_ssl(self, element: ET.Element):
        auth = element.find('{urn:ietf:params:xml:ns:xmpp-sasl}auth')
        mechanism = auth.attrib.get('mechanism')

        if not auth or not mechanism or mechanism != MECHANISM.EXTERNAL.value:
            self._transport.write(SE.bad_request())
            return Signal.FORCE_CLOSE

        ssl_cert = self._transport.get_extra_info("ssl_object")
        if ssl_cert is not None:
            cert = ssl_cert.getpeercert()
            if self.validate_domain_in_cert(cert, metadata.HOST):
                self._transport.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
                self._stage = Stage.READY
                return Signal.RESET

        else:
            self._transport.write(SE.not_authorized())
            return Signal.FORCE_CLOSE

    @staticmethod
    def validate_domain_in_cert(cert: dict, expected_domain: str) -> bool:
        alt_names = [
            v for (k, v) in cert.get("subjectAltName", []) if k == "DNS"
        ]
        common_names = [
            v for s in cert.get("subject", [])
            for (k, v) in s if k == "commonName"
        ]
        return expected_domain in alt_names or expected_domain in common_names
