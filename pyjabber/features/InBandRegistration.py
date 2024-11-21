from xml.etree import ElementTree as ET


class InBandRegistration(ET.Element):
    def __init__(
        self,
        tag: str = "register",
        attrib=None,
            **extra: str) -> None:
        super().__init__(tag, attrib, **extra)
        if attrib is None:
            attrib = {
                "xmlns": "http://jabber.org/features/iq-register"
            }
