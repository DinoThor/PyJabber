from xml.etree import ElementTree as ET


class ResourceBinding(ET.Element):
    """
    ResourceBinding Stream message.

    Allows the user to use a specific identifier for his session.
    If not provided, the server will automatically assign one in behalf of the client.
    """
    def __init__(self) -> None:
        super().__init__("bind", {"xmlns": "urn:ietf:params:xml:ns:xmpp-bind"})
