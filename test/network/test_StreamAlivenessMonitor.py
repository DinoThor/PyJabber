import asyncio
import pytest
from unittest.mock import Mock
from pyjabber.network.StreamAlivenessMonitor import StreamAlivenessMonitor

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class MonitorContext:
    def __init__(self, mon, callback):
        self.mon = mon
        self.callback = callback

    async def __aenter__(self):
        return self.mon, self.callback

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mon._timeout_task:
            self.mon._timeout_task.cancel()
            try:
                await asyncio.wait_for(self.mon._timeout_task, timeout=0.1)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                pass


@pytest.fixture
def monitor(event_loop):
    callback = Mock()
    mon = StreamAlivenessMonitor(timeout=0.1, callback=callback)
    return MonitorContext(mon, callback)


async def test_initialization(monitor):
    async with monitor as (mon, _):
        assert mon._timeout == 0.1
        assert mon._timeout_task is None


async def test_reset(monitor):
    async with monitor as (mon, _):
        mon.reset()
        assert mon._timeout_task is not None
        await asyncio.sleep(0.05)
        assert not mon._timeout_task.done()


async def test_callback_not_called_before_timeout(monitor):
    async with monitor as (mon, callback):
        mon.reset()
        await asyncio.sleep(0.05)
        callback.assert_not_called()


async def test_callback_called_after_timeout(monitor):
    async with monitor as (mon, callback):
        mon.reset()
        await asyncio.sleep(0.15)
        callback.assert_called_once()


async def test_reset_prevents_callback(monitor):
    async with monitor as (mon, callback):
        mon.reset()
        await asyncio.sleep(0.05)
        mon.reset()
        await asyncio.sleep(0.07)
        callback.assert_not_called()
