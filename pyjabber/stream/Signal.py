from enum import Enum


class Signal(Enum):
    RESET = 0
    DONE = 1
    FORCE_CLOSE = 2

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return self.value == other.value
