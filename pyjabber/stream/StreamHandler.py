import base64
from enum import Enum
import hashlib
import shelve

from loguru import logger
from uuid import uuid4
from xml.etree import ElementTree as ET
from stream.Stream import Stream
from features.StartTLSFeature import StartTLSFeature
from features.StreamFeature import StreamFeature
from features.SASLFeature import SASLFeature
from features.ResourceBinding import ResourceBinding
from network.ConnectionsManager import ConectionsManager

class Stage(Enum):
    """
    Stream connection states.
    """
    CONNECTED   = 0
    OPENED      = 1
    SSL         = 2
    SASL        = 3
    AUTH        = 4
    BIND        = 5
    READY       = 6

class Signal(Enum):
    RESET   = 0
    DONE    = 1

class StreamHandler():
    def __init__(self, buffer, starttls) -> None:
        self._buffer        = buffer
        self._starttls      = starttls

        self._streamFeature = StreamFeature()
        self._connections   = ConectionsManager()
        self._stage         = Stage.CONNECTED

        self._elem          = None

        self._jid           = None

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        self._buffer = value

    def handle_open_stream(self, elem:ET.Element = None) -> Signal | None:
        if self._stage == Stage.CONNECTED:
            self._streamFeature.reset()
            self._streamFeature.register(StartTLSFeature())
            self._buffer.write(self._streamFeature.tobytes())
            
            self._stage = Stage.OPENED

        elif self._stage == Stage.OPENED:
            if "starttls" in elem.tag:
                self._buffer.write(StartTLSFeature().proceedResponse())
                self._starttls()
                self._stage = Stage.SSL
                return Signal.RESET
        
        elif self._stage == Stage.SSL:
            self._streamFeature.reset()
            self._streamFeature.register(SASLFeature())
            self._buffer.write(self._streamFeature.tobytes())

            self._stage = Stage.SASL
        
        elif self._stage == Stage.SASL:
            if "auth" in elem.tag:
                with shelve.open("./network/users/credentials") as credStorage:

                    data        = base64.b64decode(elem.text).split("\x00".encode())
                    self._jid   = data[1].decode()
                    keyhash     = hashlib.sha256(data[2]).hexdigest()

                    try:

                        if credStorage[data[1].decode()] == keyhash:
                            self._buffer.write(SASLFeature().success())
                            self._stage = Stage.AUTH
                        else:
                            self._buffer.write(SASLFeature().not_authorized())

                    except KeyError:
                        if self._connections.autoRegister:
                            credStorage[data[1].decode()] = keyhash
                            self._buffer.write(SASLFeature().success())
                            self._stage = Stage.AUTH
                        else:
                            logger.info("Auth tag without credentials")
                            self._buffer.write(SASLFeature().not_authorized())

                return Signal.RESET
            
        elif self._stage == Stage.AUTH:
            self._streamFeature.reset()
            self._streamFeature.register(ResourceBinding())
            self._buffer.write(self._streamFeature.tobytes())
            self._stage = Stage.BIND

        elif self._stage == Stage.BIND:
            if "iq" in elem.tag:
                if elem.attrib["type"] == "set":
                    bindElem = elem.find("urn:ietf:params:xml:ns:xmpp-bind#bind")
                    if bindElem.text:   # Client gives the identifier
                        pass   # TODO: Use given resource
                    else:               # Server generates the identifier
                        iqRes = ET.Element(
                            "iq", 
                            attrib = {
                                "id": elem.attrib["id"],
                                "type": "result"
                            }
                        )
                        
                        bindRes = ET.Element(
                            "bind",
                            attrib = {
                                "xmlns": "urn:ietf:params:xml:ns:xmpp-bind"
                            }
                        )
                        jidRes = ET.Element("jid")
                        jidRes.text = f"{self._jid}@localhost/{str(uuid4())}"
                        bindRes.append(jidRes)
                        iqRes.append(bindRes)

                        self._buffer.write(ET.tostring(iqRes))

                        # Stream is negotiated.
                        # Update the connection register 
                        # with the jid and transport
                        self._connections.setJID(
                            self._buffer.get_extra_info('peername'), 
                            jidRes.text, self._buffer
                        )
                        
            return Signal.DONE