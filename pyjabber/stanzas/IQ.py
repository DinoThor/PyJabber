from enum import Enum
import xml.etree.ElementTree as ET

class IQ(ET.Element):
    class TYPE(Enum):
        GET     = "get"
        RESULT  = "result"
        SET     = "set"
        ERROR   = "error"

    def __init__(
            self,
            type: TYPE, 
            id: str     = None,
            from_: str  = None,
            to: str     = None,
            tag: str    = "iq", 
            **extra: str) -> None:
                
        attrib = {
            k: v for k, v in (
                ("id", id), 
                ("from", from_), 
                ("to", to), 
                ("type", type)) if v is not None
        }

        super().__init__(tag, attrib, **extra)
