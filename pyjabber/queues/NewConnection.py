class NewConnectionWrapper:
    """
    Represents a new connection made.
    It can be from a client or a server.
    """
    __slots__ = ('value', 'client')
    def __init__(self, value, client=True):
        self.value = value
        self.client = client
