"""The one Playwright instance of this process, on its own thread.

Playwright's async API runs on a background event loop; the test thread hands it coroutines
with ``run(coro, timeout)`` and waits for the result. Why not the sync API:

- every call has a timeout - a page blocked by a modal browser UI (print preview, a native
  prompt) raises ``TimeoutError`` instead of hanging the run;
- events are handled while the test thread waits or works with the native UI: JavaScript
  dialogs are answered at once, console messages collected, video frames received;
- any thread may call ``run`` (the video recorder does).

We only ever attach to a browser we started ourselves (``connect_over_cdp``): no browser is
downloaded or launched by Playwright, so ``playwright install`` is never needed.
"""
from __future__ import annotations

import asyncio
import atexit
import os
import threading

from sbtest.utils import log

#: seconds a single browser command may take when the caller gives no timeout
COMMAND_TIMEOUT = 30.0

_lock = threading.Lock()
_runtime: "Runtime | None" = None


class Runtime:
    def __init__(self) -> None:
        # HTTP(S)_PROXY (company proxy) must not be used to reach DevTools or the local site;
        # set before the Playwright driver process starts, which inherits the environment
        for var in ("NO_PROXY", "no_proxy"):
            current = [h.strip() for h in os.environ.get(var, "").split(",") if h.strip()]
            os.environ[var] = ",".join(current + [h for h in ("localhost", "127.0.0.1") if h not in current])
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._serve, name="sbtest-playwright", daemon=True)
        self._thread.start()
        self.playwright = self.run(self._start(), 60)

    def _serve(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    @staticmethod
    async def _start():
        from playwright.async_api import async_playwright

        return await async_playwright().start()

    def run(self, coro, timeout: float | None = None, what: str = ""):
        """Run ``coro`` on the Playwright thread and return its result. Raises the builtin
        ``TimeoutError`` when the browser does not answer within ``timeout`` seconds."""
        if threading.current_thread() is self._thread:
            coro.close()
            raise RuntimeError("runtime.run() called from a Playwright event handler: await the call instead")
        timeout = COMMAND_TIMEOUT if timeout is None else timeout
        future = asyncio.run_coroutine_threadsafe(asyncio.wait_for(coro, timeout), self.loop)
        try:
            return future.result()
        except asyncio.TimeoutError:   # the builtin TimeoutError itself from Python 3.11
            raise TimeoutError(f"the browser did not answer within {timeout:g}s"
                               + (f": {what}" if what else "")) from None

    def stop(self) -> None:
        try:
            self.run(self.playwright.stop(), 10)
        except Exception as e:  # noqa: BLE001 - process is exiting
            log.debug("playwright stop: %s", e)
        self.loop.call_soon_threadsafe(self.loop.stop)


def runtime() -> Runtime:
    """The process-wide runtime, started on first use."""
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = Runtime()
            atexit.register(_shutdown)
        return _runtime


def _shutdown() -> None:
    global _runtime
    if _runtime is not None:
        _runtime.stop()
        _runtime = None
