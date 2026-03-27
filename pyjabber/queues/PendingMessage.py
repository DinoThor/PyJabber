from dataclasses import dataclass
from typing import Optional

from pyjabber.stream.JID import JID

@dataclass(frozen=True, slots=True)
class PendingMessageWrapper:
    """
    Represents messages that could not be sent at the time of the request.

    This includes messages for local clients who are currently disconnected,
    as well as messages destined for entities on external servers that not have
    an open connection.
    """
    jid: JID
    payload: bytes
    external_host: Optional[str] = None

    @property
    def is_external(self):
        """
        Indicates whether this message is for an external protocols or not.

        Returns:
            bool: True if this message is for an external protocols or not.
        """
        return self.external_host is not None
