import xml.etree.ElementTree as ET

from pyjabber.stream.JID import JID
from pyjabber.stream.StanzaHandler import StanzaHandler


class StanzaServerIncomingHandler(StanzaHandler):
    def __init__(self, buffer) -> None:
        super().__init__(buffer)

        self._functions = {
            "{jabber:server}iq": self.handle_iq,
            "{jabber:server}message": self.handle_msg,
            "{jabber:server}presence": self.handle_pre
        }

    def handle_iq(self, element: ET.Element):
        return

    def handle_pre(self, element: ET.Element):
        pass

    def handle_msg(self, element: ET.Element):
        jid = JID(element.attrib["to"])

        if not jid.resource:
            priority = self._presenceManager.most_priority(jid)
            if not priority and self._message_persistence:
                self._message_queue.put_nowait(('MESSAGE', JID(jid.bare()), ET.tostring(element)))
                return None

            all_resources_online = []
            for user in priority:
                all_resources_online += self._connections.get_buffer_online(
                    JID(user=jid.user, domain=jid.domain, resource=user[0]))
            for buffer in all_resources_online:
                buffer[1].write(ET.tostring(element))
        else:
            resource_online = self._connections.get_buffer_online(jid)
            if not resource_online and self._message_persistence:
                self._message_queue.put_nowait(('MESSAGE', jid, ET.tostring(element)))
            else:
                for buffer in resource_online:
                    buffer[1].write(ET.tostring(element))
