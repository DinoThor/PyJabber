from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewConnectionWrapper:
    """
    Represents a new connection made.
    It can be from a client or a server.
    """
    value: str
    client: bool = True
