from pyjabber.network.XMLProtocol import XMLProtocol


class XMLProtocolS2S(XMLProtocol):
    def __init__(self, namespace, host, connection_timeout):
        super().__init__(namespace, connection_timeout)
        self._host = host

