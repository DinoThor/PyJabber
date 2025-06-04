from enum import Enum


class Signal(Enum):
    RESET = 0
    CLEAR = 1
    DONE = 2
    FORCE_CLOSE = 3

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return self.value == other.value
