from typing import Union
from xml.etree import ElementTree as ET


class Message(ET.Element):
    def __init__(
            self,
            mto: str,
            mfrom: str,
            id: str,
            body: Union[str, ET.Element],
            mtype: Union[str, None] = "chat",
            tag: str = "message",
            **extra: str) -> None:

        attrib = {
            k: v for k, v in (
                ("id", id),
                ("from", mfrom),
                ("to", mto),
                ("type", mtype)) if v is not None
        }

        super().__init__(tag, attrib, **extra)

        if type(body) == str:
            body_elem = ET.Element("body")
            body_elem.text = body
            self.append(body_elem)

        else:
            self.append(body)
