from enum import Enum


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
    NONE = 'none'
    PENDING = 'pending'
    UNCONFIGURED = 'unconfigured'
    SUBSCRIBED = 'subscribed'


class NodeAccess(Enum):
    OPEN = 0
    PRESENCE = 1
    ROSTER = 2
    AUTHORIZE = 3
    WHITELIST = 4


class Affiliation:
    OWNER = 'owner'
    PUBLISHER = 'publisher'
    MEMBER = 'member'
    NONE = 'none'
    OUTCAST = 'outcast'
