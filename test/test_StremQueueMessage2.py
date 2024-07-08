import pytest
import asyncio
from unittest.mock import MagicMock
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stream.QueueMessage import QueueMessage

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def setup_queue_message(event_loop):
    connection_manager = MagicMock(ConnectionManager)
    queue_message = QueueMessage(connection_manager, loop=event_loop)
    return queue_message, connection_manager



@pytest.mark.asyncio
async def test_chrono_no_buffer(setup_queue_message):
    queue_message, connection_manager = setup_queue_message
    host = 'test_host'
    element = b'<message>Test</message>'

    connection_manager.get_server_buffer.return_value = None

    queue_message.enqueue(host, element)

    await asyncio.sleep(6)  # Esperar a que se ejecute la tarea chrono

    connection_manager.get_server_buffer.assert_called_with(host)
    assert len(queue_message._queue) == 1  # Elemento sigue en la cola

if __name__ == "__main__":
    pytest.main()
