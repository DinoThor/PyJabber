from enum import Enum


class PresenceShow(Enum):
    EXTENDED_AWAY = "xa"
    AWAY = "away"
    CHAT = "chat"
    DND = "dnd"
    NONE = "none"


class PresenceType(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
