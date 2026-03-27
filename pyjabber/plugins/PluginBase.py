from xml.etree.ElementTree import Element

from pyjabber.stream.JID import JID


class PluginBase:
    async def feed(self, jid: JID, element: Element):
        """
        The endpoint for any plugin implemented in the protocols
        A plugin may include in the return statement a response message (in bytes) to the client
        """
        raise NotImplementedError
