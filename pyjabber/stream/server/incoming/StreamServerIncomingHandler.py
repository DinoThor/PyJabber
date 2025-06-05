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

    def __init__(self, transport, starttls, parser_ref) -> None:
        super().__init__(transport, starttls, parser_ref)



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
