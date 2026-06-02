from enum import Enum
from typing import Optional, TypedDict

from pyjabber.features.presence.Enums import PresenceType


class ResourcePresence(TypedDict):
    presence_type: PresenceType
    status: Optional[str]
    show: Optional[str]
    priority: Optional[int]

class JIDPresence(TypedDict):
    resource: ResourcePresence

class PIMType(Enum):
    SERVER = "server"
    CLIENT = "client"

class PresenceInternalMessage(TypedDict):
    type: PIMType
    value: str

