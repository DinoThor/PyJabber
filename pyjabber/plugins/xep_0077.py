from xml.etree.ElementTree import Element
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.plugins.PluginInterface import Plugin


class inBandRegistration(Plugin):
    def __init__(self) -> None:
        super().__init__()
        self._autoregister = ConectionsManager().autoRegister()

    def feed(self, jid: str, element: Element):
        pass