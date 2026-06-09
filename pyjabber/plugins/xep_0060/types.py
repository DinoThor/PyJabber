from enum import Enum
from typing import Optional, TypedDict


class NodeRepository(TypedDict):
    pass


class Node(TypedDict):
    node: str
    owner: str
    name: Optional[str]
    type: str
    max_items: int


class NodeItem(TypedDict):
    node: str
    publisher: str
    item_id: str
    payload: bytes


class Subscriber(TypedDict):
    node: str
    jid: str
    subid: str
    subscription: str
    affiliation: str


class NodeAttrib(Enum):
    NODE = 0
    OWNER = 1
    NAME = 2
    TYPE = 3
    MAXITEMS = 4


class SubscribersAttrib(Enum):
    NODE = 0
    JID = 1
    SUBID = 2
    SUBSCRIPTION = 3
    AFFILIATION = 4


class Subscription(Enum):
    NONE = "none"
    PENDING = "pending"
    UNCONFIGURED = "unconfigured"
    SUBSCRIBED = "subscribed"


class Affiliation:
    OWNER = "owner"
    PUBLISHER = "publisher"
    MEMBER = "member"
    NONE = "none"
    OUTCAST = "outcast"
