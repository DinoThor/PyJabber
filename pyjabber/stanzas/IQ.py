import xml.etree.ElementTree as ET
from enum import Enum
from uuid import uuid4


class IQ(ET.Element):
    """
    An IQ stanza element based on ElementTree.
    The enum TYPE define the possible values of type
    """
    class TYPE(Enum):
        GET = "get"
        RESULT = "result"
        SET = "set"
        ERROR = "error"

    def __init__(
            self,
            type_: TYPE,
            id_: str = None,
            from_: str = None,
            to: str = None,
            **extra: str) -> None:
        """
        Create an IQ stanza

        Args:
            type (IQ.TYPE): A value of IQ.TYPE enum indicating the type of the iq stanza
            id (str): Optional string identifier of the stanza
            from_ (str): The sender user
            to (str): The receiver user
        """
        attrib = {
            k: v for k, v in (
                ("id", id_),
                ("from", from_),
                ("to", to),
                ("type", type_.value)) if v is not None
        }

        if attrib.get('id') is None:
            attrib['id'] = str(uuid4())

        super().__init__('iq', attrib, **extra)
