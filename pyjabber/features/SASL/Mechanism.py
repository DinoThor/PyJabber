from enum import Enum


class MECHANISM(Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"
    EXTERNAL = "EXTERNAL"
