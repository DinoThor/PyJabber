from enum import Enum


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
