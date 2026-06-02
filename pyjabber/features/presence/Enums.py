from enum import Enum


class PresenceShow(Enum):
    EXTENDED_AWAY = "xa"
    AWAY = "away"
    CHAT = "chat"
    DND = "dnd"
    NONE = "none"


PresenceShowWeights = {
    PresenceShow.EXTENDED_AWAY: 0,
    PresenceShow.AWAY: 1,
    PresenceShow.DND: -1,
    PresenceShow.NONE: 2,
    PresenceShow.CHAT: 3,
}


class PresenceType(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
