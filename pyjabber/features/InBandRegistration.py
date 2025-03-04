from xml.etree import ElementTree as ET


class InBandRegistration(ET.Element):
    """
    InBandRegistration Stream message.

    It allows the user to register itself on the server if
    there is no credentials stored with the given JID
    """
    def __init__(
        self,
        tag: str = "register",
        attrib=None,
            **extra: str) -> None:

        default_atrrib = {
            "xmlns": "http://jabber.org/features/iq-register"
        }

        super().__init__(tag, attrib or default_atrrib, **extra)
