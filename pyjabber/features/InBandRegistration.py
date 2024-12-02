from xml.etree import ElementTree as ET


class InBandRegistration(ET.Element):
    def __init__(
        self,
        tag: str = "register",
        attrib=None,
            **extra: str) -> None:

        default_atrrib = {
            "xmlns": "http://jabber.org/features/iq-register"
        }

        super().__init__(tag, attrib or default_atrrib, **extra)
