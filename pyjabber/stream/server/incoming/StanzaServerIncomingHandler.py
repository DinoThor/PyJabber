import os
import xml.etree.ElementTree as ET

from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.StanzaHandler import StanzaHandler

try:
    from typing import override
except ImportError:
    def override(func): return func


class StanzaServerIncomingHandler(StanzaHandler):
    def __init__(self, buffer) -> None:
        super().__init__(buffer)

    @override
    def feed(self, element: ET.Element):
        ssl_cert = self._buffer.get_extra_info("ssl_object")
        from_ = element.attrib.get("from")
        from_ = from_.split("@").pop() if from_ else None

        if not from_:
            pass

        if not self.verify_claimed_domain(ssl_cert, from_):
            pass

        try:
            self._functions[element.tag](element)
        except KeyError:
            self._buffer.write(SE.bad_request())

    @staticmethod
    def verify_claimed_domain(cert: dict, expected_domain: str) -> bool:
        san = cert.get("subjectAltName", [])
        for key, value in san:
            if key == "DNS" and value.lower() == expected_domain.lower():
                return True

        for item in cert.get("subject", []):
            for key, value in item:
                if key == "commonName" and value.lower() == expected_domain.lower():
                    return True

        return False
