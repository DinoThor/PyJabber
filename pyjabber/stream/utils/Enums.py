from enum import Enum


class Signal(Enum):
    RESET = 0
    STARTTLS = 1
    CLEAR = 2
    DONE = 3
    FORCE_CLOSE = 4


class Stage(Enum):
    """
    Stream connection states.
    """
    CONNECTED = 0
    OPENED = 1
    SSL = 2
    SASL = 3
    AUTH = 4
    BIND = 5
    READY = 6
