import asyncio
import warnings


class StreamAlivenessMonitor:
    '''
    This class is a helper to monitor the aliveness of a stream. It will call a callback if the stream is not alive after a timeout.
    '''

    __slots__ = ["_timeout", "_timeout_callback", "_timeout_task", "_reset_event"]

    def __init__(self, timeout=60, callback=None):
        self._timeout = timeout
        self._timeout_callback = callback
        self._timeout_task = None
        self._reset_event = asyncio.Event()

    def __del__(self):
        if self._timeout_task is not None:
            self._timeout_task.cancel()

    async def _timeout_task_coro(self):
        await asyncio.wait_for([self._reset_event.wait()], timeout=self._timeout)
        if self._timeout_callback is not None:
            self._timeout_callback()

    def reset(self):
        if self._timeout_task is not None:
            self._reset_event.set()
            self._timeout_task.cancel()
        self._reset_event.clear()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._timeout_task = asyncio.create_task(self._timeout_task_coro())
