from attrs import define


@define(frozen=True, slots=True)
class FailedRemoteConnectionWrapper:
    """
    Represents a S2S connection failure.
    Notifies to the client with pending messages to the remote server
    """

    value: str
    reason: str
