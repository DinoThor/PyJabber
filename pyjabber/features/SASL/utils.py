from xml.etree import ElementTree as ET
from uuid import uuid4

from pyjabber import AppConfig


def validate_cert(from_claim, cert):
    peer_cert = cert.getpeercert()
    cert_names = set()

    subject = peer_cert.get("subject", [])
    for attr in subject:
        for (key, value) in attr:
            if key == "commonName":
                cert_names.add(value)

    for typ, value in peer_cert.get("subjectAltName", []):
        if typ == "DNS":
            cert_names.add(value)

    return from_claim in cert_names

def iq_register_result(iq_id: str) -> bytes:
    iq = ET.Element(
        "iq",
        attrib={
            "type": "result",
            "id": iq_id or str(uuid4()),
            "from": AppConfig.app_config.host})
    return ET.tostring(iq)

def not_authorized_response() -> bytes:
    return b"<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'><not-authorized/></failure></stream>"

def success_response() -> bytes:
    return b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
