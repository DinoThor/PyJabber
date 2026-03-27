
class FailedRemoteConnectionWrapper:
    """
    Represents a S2S connection failure.
    Notifies to the client with pending messages to the remote server
    """
    __slots__ = ('value', 'reason')
    def __init__(self, value, reason):
        self.value = value
        self.reason = reason
