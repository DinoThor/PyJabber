from xml.etree import ElementTree as ET

class NonUniqueFeature(Exception):
    """
    Exception raised when a non unique feature is found on the manager
    """
    pass

class StreamFeature(ET.Element):
    """Class to manage server features."""
    __slots__ = [
        "_features"
    ] 

    def __init__(
            self, 
            tag     : str               = "stream:features", 
            attrib  : dict[str, str]    = {
                "xmlns": "http://etherx.jabber.org/streams"
            }, 
            **extra : str) -> None:
        super().__init__(tag, attrib, **extra)
        self._features: dict[str, ET.Element] = {}

    def register(self, feature: ET.Element):
        """
        Register a new feature
        """
        if feature.tag in self._features.keys():
            raise NonUniqueFeature("Feature already registered")
        self._features[feature.tag] = feature

    def unregister(self, feature):
        """
        Unregister a feature
        """
        if feature.tag in self._features:
            del self._features[feature.tag]

    def reset(self):
        """
        Remove all features registered in the
        StreamFeature object.
        """
        self._features.clear()


    def tostring(self) -> str:
        """
        Return a string representation of the xml message
        """
        return self.tobytes().decode()

    def tobytes(self) -> bytes:
        """
        Return an encoded xml message
        """
        res = self.__copy__()
        for _, feature in self._features.items():
            res.append(feature)

        return ET.tostring(res)
