from enum import Enum
from typing import Dict
from xml.etree import ElementTree as ET


def proceed_response() -> bytes:
    """
    Proceed Stream message.

    Indicates that the TLS upgrade process has started.
    """
    elem = ET.Element(
        "proceed", attrib={
            "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"
        }
    )
    return ET.tostring(elem)


class StartTLSFeature(ET.Element):
    """
    STARTTLS Stream message.

    Indicates to the user that the server is ready for the TLS upgrade (handshake).
    """
    def __init__(
        self,
        tag: str = "starttls",
        attrib: Dict[str, str] = None,
        required: bool = True,
            **extra: str) -> None:

        default_attrib = {
            "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"
        }

        super().__init__(tag, attrib or default_attrib, **extra)

        if required:
            self.append(ET.Element("required"))
