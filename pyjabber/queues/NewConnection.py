from typing import Union

from attrs import define

from pyjabber.stream.JID import JID


@define(frozen=True, slots=True)
class NewConnectionWrapper:
    """
    Represents a new connection made.
    It can be from a client or a server.
    """

    value: Union[str, JID]
    client: bool = True
