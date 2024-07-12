import asyncio
import pytest
from unittest.mock import MagicMock, patch
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor


@pytest.fixture
def monitor():
    callback = MagicMock()
    mon = StreamAlivenessMonitor(timeout=1, callback=callback)
    return mon, callback


@pytest.mark.asyncio
async def test_timeout_callback_called(monitor):
    mon, callback = monitor
    mon.reset()  # Asegúrate de iniciar el monitor

    await asyncio.sleep(1.5)

    try:
        callback.assert_called_once()
    except AssertionError as e:
        print(f"AssertionError: {e}")
        print(f"Callback call count: {callback.call_count}")
        print(f"Was the timeout coroutine awaited?: {mon._timeout_task is not None and not mon._timeout_task.done()}")
        raise e




def test_monitor_initialization(monitor):
    mon, _ = monitor
    assert mon._timeout_task is None

@pytest.mark.asyncio
async def test_monitor_reset(monitor):
    mon, _ = monitor
    mon.reset()
    assert mon._timeout_task is not None
    assert not mon._timeout_task.done()



@pytest.mark.asyncio
async def test_reset(monitor):
    mon, callback = monitor
    mon.reset()
    assert mon._timeout_task is not None

    await asyncio.sleep(0.5)
    mon.reset()
    await asyncio.sleep(0.5)
    callback.assert_not_called()

    await asyncio.sleep(1.5)
    callback.assert_called_once()

@pytest.mark.asyncio
@patch('pyjabber.network.StreamAlivenessMonitor.asyncio.create_task')
async def test_reset_creates_task(mock_create_task, monitor):
    mon, callback = monitor
    mon.reset()
    await asyncio.sleep(0.1)
    mock_create_task.assert_called_once()

    called_coroutine = mock_create_task.call_args[0][0]
    assert asyncio.iscoroutine(called_coroutine)
    assert called_coroutine.__name__ == mon._timeout_task_coro().__name__


@pytest.fixture(autouse=True)
def cleanup(monitor):
    yield
    mon, callback = monitor
    if mon._timeout_task is not None:
        mon._timeout_task.cancel()

