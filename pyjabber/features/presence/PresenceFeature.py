import asyncio
import xml.etree.ElementTree as ET
from contextlib import closing
from enum import Enum
from typing import Any, Dict, Tuple, List, Union
from uuid import uuid4
from xml.etree.ElementTree import Element

from sqlalchemy import select, delete

from pyjabber import metadata
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.features.feature_utils import RosterUtils as RU
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


class PresenceShow(Enum):
    EXTENDED_AWAY = "xa"
    AWAY = "away"
    CHAT = "chat"
    DND = "dnd"
    NONE = "none"


class PresenceType(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Presence(metaclass=Singleton):
    def __init__(self) -> None:
        self._handlers = {
            "subscribe": self.handle_subscribe,
            "subscribed": self.handle_subscribed,
            "unsubscribed": self.handle_unsubscribed,
            "unavailable": self.handle_global_presence,
            "INTERNAL": self.handle_lost_connection
        }
        self._connections = ConnectionManager()
        self._roster = Roster()

        self._pending = {}
        self._get_all_pending_presence()
        self._connection_queue: asyncio.Queue = metadata.CONNECTION_QUEUE

        self._online_status = {}

    def _get_all_pending_presence(self):
        with DB.connection() as con:
            query = select(Model.PendingSubs.c.jid, Model.PendingSubs.c.item)
            res = con.execute(query).fetchall()
            # res = con.execute("SELECT jid, item FROM pendingsub", ())
            # res = res.fetchall()
        for jid_from, jid_to, item in res:
            if jid_to not in self._pending:
                self._pending[jid_to] = [item]
            else:
                self._pending[jid_to].append(item)

    def _update_pending_presence(self):
        pass

    def _delete_pending_presence(self, jid: str):
        with DB.connection() as con:
            query = delete(Model.PendingSubs).where(Model.PendingSubs.c.jid == jid)
            con.execute()
            # con.execute("DELETE FROM pendingsub WHERE jid = ?", (jid,))
            con.commit()
        self._pending[jid].pop()

    def priority_by_jid(self, jid: JID):
        try:
            return self._online_status[jid.bare()]
        except KeyError:
            return []

    def most_priority(self, jid: JID) -> List[Tuple[str, PresenceType, Union[str, None], Union[str, None], Union[str, None]]]:
        priority = self.priority_by_jid(jid)

        values = [item[-1] for item in priority if item[-1] is not None]
        max_value = max(values) if values else None
        return [item for item in priority if item[-1] == max_value]

    def feed(self, jid: JID, element: Element, extra: Dict[str, Any] = None):
        if "type" in element.attrib:
            return self._handlers[element.get("type")](jid, element)

        if "to" not in element.attrib:
            return self.handle_global_presence(jid, element)

        return None

    def handle_lost_connection(self, jid: JID, element: Element):
        if jid.bare() not in self._online_status:
            return None

        index, present = self._present_in_online_list(jid)
        if present:
            if self._online_status[jid.bare()][index][1] == PresenceType.UNAVAILABLE:
                self._online_status[jid.bare()].pop(index)
                if len(self._online_status[jid.bare()]) == 0:
                    self._online_status.pop(jid.bare())
                return None

        for contact in self._roster.roster_by_jid(jid):
            item = ET.fromstring(contact.get("item"))
            if item.attrib.get("subscription") not in ["from", "both"]:
                continue

            contact_jid = item.attrib.get("jid")

            if len(contact_jid.split("@")) < 2:
                contact_jid = JID(contact_jid + f"@{metadata.HOST}")
            else:
                contact_jid = JID(contact_jid)

            if contact_jid.bare() in self._online_status:
                for user_connected in [i for i in self._online_status[contact_jid.bare()] if
                                       i[1] == PresenceType.AVAILABLE]:
                    resource = user_connected[0]
                    dest_jid, buffer, _ = self._connections.get_buffer(
                        JID(user=contact_jid.user, domain=contact_jid.domain, resource=resource))[0]

                    presence = ET.Element(
                        "presence",
                        attrib={
                            "from": str(jid),
                            "to": dest_jid.bare(),
                            "type": PresenceType.UNAVAILABLE.value
                        }
                    )
                    buffer.write(ET.tostring(presence))

        for _, neighbour_resource, _ in self._connections.get_buffer(JID(jid.bare())):
            presence = ET.Element(
                "presence",
                attrib={
                    "from": str(jid),
                    "to": jid.bare(),
                    "type": PresenceType.UNAVAILABLE.value
                }
            )
            neighbour_resource.write(ET.tostring(presence))

    def handle_global_presence(self, jid: JID, element: ET.Element):
        if jid.bare() not in self._online_status:
            self._online_status[jid.bare()] = []

        show = next((c.text for c in element if c.tag == '{jabber:client}show' and c.text in [i.value for i in PresenceShow]), None)
        status = next((c.text for c in element if c.tag == '{jabber:client}status'), None)
        priority = next((c.text for c in element if c.tag == '{jabber:client}priority'), None)

        index, present = self._present_in_online_list(jid)
        if element.attrib.get("type") == PresenceType.UNAVAILABLE.value:
            if present:
                self._online_status[jid.bare()][index] = (
                    jid.resource, PresenceType.UNAVAILABLE, show, status, priority
                )
            else:
                self._online_status[jid.bare()].append(
                    (jid.resource, PresenceType.UNAVAILABLE, show, status, priority)
                )

            self._connections.online(jid, False)
        else:
            if present:
                previous_status = self._online_status[jid.bare()][index][1]
                self._online_status[jid.bare()][index] = (jid.resource, PresenceType.AVAILABLE, show, status, priority)
                if previous_status == PresenceType.UNAVAILABLE:
                    self._connection_queue.put_nowait(('CONNECTION', jid))
            else:
                self._online_status[jid.bare()].append((jid.resource, PresenceType.AVAILABLE, show, status, priority))
                self._connection_queue.put_nowait(('CONNECTION', jid))

            self._connections.online(jid)

        for contact in self._roster.roster_by_jid(jid):
            item = ET.fromstring(contact.get("item"))
            if item.attrib.get("subscription") not in ["from", "both"]:
                continue

            contact_jid = item.attrib.get("jid")

            if len(contact_jid.split("@")) < 2:
                contact_jid = JID(contact_jid + f"@{metadata.HOST}")
            else:
                contact_jid = JID(contact_jid)

            if contact_jid.bare() in self._online_status:
                for user_connected in [i for i in self._online_status[contact_jid.bare()] if i[1] == PresenceType.AVAILABLE]:
                    resource = user_connected[0]
                    online = self._connections.get_buffer(JID(user=contact_jid.user, domain=contact_jid.domain, resource=resource))
                    online = self._connections.get_buffer(JID(user=contact_jid.user, domain=contact_jid.domain, resource=resource))
                    if online:
                        dest_jid, buffer, _ = online[0]
                        dest_jid, buffer, _ = online[0]

                        presence = ET.Element(
                            "presence",
                            attrib={
                                "from": str(jid),
                                "to": dest_jid.bare(),
                            }
                        )

                        if element.attrib.get("type") == PresenceType.UNAVAILABLE.value:
                            presence.attrib["type"] = PresenceType.UNAVAILABLE.value

                        if show:
                            show_et = ET.SubElement(presence, "show")
                            show_et.text = show

                        if status:
                            status_et = ET.SubElement(presence, "status")
                            status_et.text = status

                        if priority:
                            priority_et = ET.SubElement(presence, "priority")
                            priority_et.text = priority

                        buffer.write(ET.tostring(presence))

        if jid.bare() in self._pending:
            for item in self._pending[jid.bare()]:
                for buffer in self._connections.get_buffer(jid):
                    buffer[1].write(item)
            self._delete_pending_presence(jid.bare())

        return None

    def handle_subscribe(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle local presence. Receiver client connected to the server
        if to.domain == metadata.HOST:
            roster = self._roster.roster_by_jid(jid)

            item = [item for item in roster
                    if ET.fromstring(item.get("item")).attrib.get("jid") == to.user
                    or ET.fromstring(item.get("item")).attrib.get("jid") == to.bare()
                    ]

            if not item:
                self._roster.create_roster_entry(jid, to)
                roster = self._roster.roster_by_jid(jid)
                item = [item for item in roster
                        if ET.fromstring(item.get("item")).attrib["jid"] == to.user
                        or ET.fromstring(item.get("item")).attrib["jid"] == to.bare()
                        ]

            roster_item = item[0].get("item")
            et_item = ET.fromstring(roster_item)
            item_id = item[0].get("id")

            if et_item.attrib.get("ask") == "subscribe":
                return

            if et_item.attrib.get("subscription") in ["to", "both"]:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get('to'),
                        "to": element.attrib.get('from'),
                        "id": element.attrib.get('id') or str(uuid4()),
                        "type": "subscribed"
                    }
                )
                return ET.tostring(petition)

            if "ask" not in et_item.attrib:
                new_item = et_item.__copy__()
                new_item.attrib["ask"] = "subscribe"
                self._roster.update_item(new_item, item_id)

            buffer = self._connections.get_buffer(to)
            if buffer:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get('from'),
                        "to": element.attrib.get('to'),
                        "id": element.attrib.get('id') or str(uuid4()),
                        "type": "subscribe"
                    }
                )
                for b in buffer:
                    b[1].write(ET.tostring(petition))

            else:
                self._roster.store_pending_sub(to.bare(), element)

    def handle_subscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle local presence. Receiver client connected to the server
        if to.domain == metadata.HOST:
            roster_sender = self._roster.roster_by_jid(to)
            roster_receiver = self._roster.roster_by_jid(jid)

            if not roster_sender:
                return None

            if not roster_receiver:
                self._roster.create_roster_entry(JID(jid.bare()), to)
                roster_receiver = self._roster.roster_by_jid(jid)

            roster_push_sender = None
            roster_push_receiver = None

            item_sender = [  # Sender appears in receiver roster
                item for item in roster_sender
                if ET.fromstring(item.get("item")).attrib.get("jid") == jid.user
            ]

            item_receiver = [  # Receiver appears in sender roster
                item for item in roster_receiver
                if ET.fromstring(item.get("item")).attrib.get("jid") == to.user
            ]

            if item_sender:
                item_id = item_sender[0].get("id")
                item_sender = item_sender[0].get("item")
                et_item_sender = ET.fromstring(item_sender)

                if et_item_sender.attrib.get("subscription") == "none":
                    new_item_sender = et_item_sender.__copy__()
                    if "ask" in new_item_sender.attrib:
                        new_item_sender.attrib.pop("ask")

                    new_item_sender.attrib["subscription"] = "to"
                    self._roster.update_item(new_item_sender, item_id)

                    new_item_sender.attrib['jid'] = new_item_sender.attrib['jid'] + f"@{metadata.HOST}"
                    roster_push_sender = new_item_sender

                elif et_item_sender.attrib.get("subscription") == "from":
                    new_item_sender = et_item_sender.__copy__()
                    if "ask" in new_item_sender.attrib:
                        new_item_sender.attrib.pop("ask")

                    new_item_sender.attrib["subscription"] = "both"
                    self._roster.update_item(new_item_sender, item_id)

                    new_item_sender.attrib['jid'] = new_item_sender.attrib['jid'] + f"@{metadata.HOST}"
                    roster_push_sender = new_item_sender

                else:
                    item_sender = None

            if item_receiver:
                item_id = item_receiver[0].get("id")
                item_receiver = item_receiver[0].get("item")
                et_item_receiver = ET.fromstring(item_receiver)

                if et_item_receiver.attrib.get("subscription") == "none":
                    new_item_receiver = et_item_receiver.__copy__()
                    new_item_receiver.attrib["subscription"] = "from"
                    self._roster.update_item(new_item_receiver, item_id)

                    new_item_receiver.attrib['jid'] = new_item_receiver.attrib['jid'] + f"@{metadata.HOST}"
                    roster_push_receiver = new_item_receiver

                elif et_item_receiver.attrib["subscription"] == "to":
                    new_item_receiver = et_item_receiver.__copy__()
                    new_item_receiver.attrib["subscription"] = "both"
                    self._roster.update_item(new_item_receiver, item_id)

                    new_item_receiver.attrib['jid'] = new_item_receiver.attrib['jid'] + f"@{metadata.HOST}"
                    roster_push_receiver = new_item_receiver

                else:
                    item_receiver = None

            if item_receiver:
                for sender in self._connections.get_buffer(JID(to.bare())):
                    res = ET.Element(
                        "presence",
                        attrib={
                            "from": jid.bare(),
                            "to": str(to),
                            "id": element.attrib.get('id') or str(uuid4()),
                            "type": "subscribed",
                        },
                    )
                    sender[1].write(ET.tostring(res))
                return None

            if roster_push_sender is not None:
                for sender in self._connections.get_buffer(JID(to.bare())):
                    res = IQ(to=str(sender[0]), type_=IQ.TYPE.SET)
                    query = ET.SubElement(res, "query", attrib={"xmlns": "jabber:iq:roster"})
                    query.append(roster_push_sender)

                    sender[1].write(ET.tostring(res))

            if roster_push_receiver is not None:
                for receiver in self._connections.get_buffer(JID(jid.bare())):
                    res = IQ(to=str(receiver[0]), type_=IQ.TYPE.SET)
                    query = ET.SubElement(res, "query", attrib={"xmlns": "jabber:iq:roster"})
                    query.append(roster_push_receiver)

                    receiver[1].write(ET.tostring(res))

    def handle_unsubscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib["to"])
        # bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle locally
        if to.domain == metadata.HOST:
            roster = self._roster.roster_by_jid(jid)
            # buffer =

            item = [item for item in roster
                    if ET.fromstring(item.get("item")).attrib.get("jid") in [to.bare(), to.user]]

            if not item:
                return

            item_id = item[0].get("id")
            item = item[0].get("item")
            et_item = ET.fromstring(item)
            new_item = et_item.__copy__()

            updated = False

            if et_item.attrib.get("subscription") == "to":
                new_item.attrib["subscription"] = "none"
                self._roster.update_item(item=new_item, id_=item_id)
                updated = True

            elif et_item.attrib.get("subscription") == "both":
                new_item.attrib["subscription"] = "from"
                self._roster.update_item(item=new_item, id_=item_id)
                updated = True

            elif "ask" in et_item.attrib:
                new_item.attrib.pop("ask")
                self._roster.update_item(item=new_item, id_=item_id)

            if updated:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get('from'),
                        "to": to.bare(),
                        "id": str(uuid4()),
                        "type": "unsubscribed"
                    }
                )
                for buffer in self._connections.get_buffer(to):
                    buffer[1].write(ET.tostring(presence))
                # roster_push = ET.Element(
                #     "iq",
                #     attrib={
                #         "id": id_iq,
                #         "to": b[0],
                #         "type": "set"
                #     }
                # )
                #
                # query = ET.Element("{jabber:iq:roster}query")
                # query.append(new_item)
                # roster_push.append(query)
                #
                # b[1].write(ET.tostring(presence))
                # b[1].write(ET.tostring(roster_push))

    def handle_unavailable(self, jid: JID, element: ET.Element):
        # bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        roster = RU.retrieve_roster(jid.bare())

        for item in roster:
            to = ET.fromstring(item[-1]).attrib.get('jid')

            if to.split("@")[1] == metadata.HOST:
                presence = element.__copy__()

                presence.attrib["to"] = to

                buffer = self._connections.get_buffer(JID(to))
                for b in buffer:
                    b[1].write(ET.tostring(presence))

    def _present_in_online_list(self, jid: JID):
        if jid.bare() not in self._online_status:
            return None, None

        present = [(i,p) for i, p in enumerate(self._online_status[jid.bare()]) if p[0] == jid.resource]
        if present:
            return present[0]
        return None, None
