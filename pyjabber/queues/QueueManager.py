import asyncio
from enum import Enum, unique


@unique
class QueueName(Enum):
    CONNECTIONS = "connections"
    MESSAGES = "messages"
    SERVERS = "servers"


class QueueManager:
    _queues: dict[QueueName, asyncio.Queue] = {}

    @classmethod
    def get_queue(cls, name: QueueName, maxsize: int = 0) -> asyncio.Queue:
        if not isinstance(name, QueueName):
            raise ValueError(f"Queue name invalid. Available names: {list(QueueName)}")

        if name not in cls._queues:
            cls._queues[name] = asyncio.Queue(maxsize=maxsize)
        return cls._queues[name]


get_queue = QueueManager.get_queue
