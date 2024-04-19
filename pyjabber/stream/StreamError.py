class StreamError():
    """
    Base class for all stream errors.
    
    Represents a stream error defined in section 4.9. of RFC 6120.
    """
    __slots__ = ["_tag", "_xmlns"]

    def __init__(self, tag):
        self._tag = tag
        self._xmlns = 'urn:ietf:params:xml:ns:xmpp-streams'

class NotWellFormed(StreamError):
    """
    Stream error that represents a not well-formed XML stanza error. The stream errors are unrecoverable, 
    so the entity that detects the error MUST send an error element containing the 'not-well-formed' error condition to the other entity, 
    close the stream, and terminate the underlying TCP connection as described in section 4.9.1.1 of RFC 6120.
    """
    def __init__(self):
        super().__init__("not-well-formed")
