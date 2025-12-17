from enum import Enum


class Signal(Enum):
    RESET = 0
    STARTTLS = 1
    CLEAR = 2
    DONE = 3
    FORCE_CLOSE = 4
