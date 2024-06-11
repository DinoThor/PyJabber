import asyncio
import os
import pickle
import xml.etree.ElementTree as ET

import xmlschema

from pyjabber.features.PresenceFeature import Presence
# from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.network.server.OpenConnection import open_server_connection
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class StanzaHandler():
    def __init__(self, buffer) -> None:
        self._buffer            = buffer
        # self._connections       = ConnectionManager()
        self._peername          = buffer.get_extra_info('peername')
        self._jid               = "marc"#self._connections.get_jid_by_peer(self._peername)
        self._pluginManager     = PluginManager(self._jid)
        self._presenceManager   = Presence()

        self._functions     = {
            "{jabber:client}iq"          : self.handleIQ,
            "{jabber:client}message"     : self.handleMsg,
            "{jabber:client}presence"    : self.handlePre
        }

        with open(FILE_PATH + "/schemas/schemas.pkl", "rb") as schemasDump:
            self._schemas = pickle.load(schemasDump)

    def feed(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[0]]
            if schema.is_valid(ET.tostring(element)) is False:
                self._buffer.write(SE.bad_request())
        except KeyError:
            self._buffer.write(SE.feature_not_implemented())

        try:
            self._functions[element.tag](element)
        except KeyError:
            raise Exception()

    ############################################################
    ############################################################

    def handleIQ(self, element: ET.Element):
        res = self._pluginManager.feed(element)
        if res:
            self._buffer.write(res)

    def handleMsg(self, element: ET.Element):
        bare_jid        = element.attrib["to"].split("/")[0]

        if False:#"localhost" in bare_jid:
            reciverBuffer   = self._connections.get_buffer_by_jid(bare_jid)

            for buffer in reciverBuffer:
                buffer[-1].write(ET.tostring(element))

        else:
            print("HASDHS")
            open_server_connection(bare_jid)



    def handlePre(self, element: ET.Element):
        res = self._presenceManager.feed(element, self._jid)
        if res:
            self._buffer.write(res)

