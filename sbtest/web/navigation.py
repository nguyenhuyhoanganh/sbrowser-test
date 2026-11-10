"""Navigation, tabs/windows, iframes, JavaScript dialogs (alert/confirm/prompt), CDP, screenshots."""
from __future__ import annotations

import contextlib
from pathlib import Path

from playwright.async_api import Error as PlaywrightError

from sbtest.utils import poll


class DialogPlan:
    """What ``with web.dialog(...)`` answers and what it saw."""

    def __init__(self, accept: bool, prompt_text: str | None) -> None:
        self.accept, self.prompt_text = accept, prompt_text
        self.seen: list[dict] = []

    @property
    def text(self) -> str:
        """Message of the first dialog ("" when none showed)."""
        return self.seen[0]["message"] if self.seen else ""

    @property
    def type(self) -> str:
        """alert | confirm | prompt | beforeunload of the first dialog."""
        return self.seen[0]["type"] if self.seen else ""

    @property
    def messages(self) -> list[str]:
        return [d["message"] for d in self.seen]


class NavigationMixin:
    # -- pages -----------------------------------------------------------------
    def open(self, url: str, wait: bool = True, blocking: bool = True) -> None:
        """Open a URL (http/file/chrome://...) in the current tab.

        ``blocking=False`` navigates through ``location.href`` and returns at once - use it
        when the navigation stops at a browser prompt (HTTP sign-in), otherwise the call
        would wait for a page load that only happens after the prompt.
        """
        preloaded, self.preloaded_url = getattr(self, "preloaded_url", ""), ""
        self._frames.clear()
        if blocking and wait and preloaded and url.rstrip("/") == preloaded.rstrip("/") \
                and self.url.rstrip("/") == url.rstrip("/"):
            # the browser start already sent the first tab here (browser.start_page): no reload
            self.wait_ready()
            return
        if not blocking:
            self.js("setTimeout(() => { location.href = arguments[0]; }, 0);", url)
            return
        self.run(self._goto(url), self.page_load_timeout + 5, f"open {url}")
        if wait:
            self.wait_ready()

    async def _goto(self, url: str) -> None:
        try:
            await self.page.goto(url, wait_until="load", timeout=self.page_load_timeout * 1000)
        except PlaywrightError as e:
            if "Download is starting" not in str(e):   # a URL that downloads has no page to wait for
                raise

    def open_internal(self, name: str) -> None:
        """Internal page by logical name from config ``pages`` (bookmarks, history, settings...)."""
        self.open(self.cfg.page_url(name))

    def back(self) -> None:
        self.run(self.page.go_back())

    def forward(self) -> None:
        self.run(self.page.go_forward())

    def refresh(self) -> None:
        self.run(self.page.reload())

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.run(self.page.title())

    # -- tabs ------------------------------------------------------------------
    @property
    def tabs(self) -> list:
        """The open tabs and popup windows (Playwright pages), oldest first."""
        return list(self.context.pages)

    def _use(self, page):
        self.page = page
        self._frames.clear()
        return page

    def new_tab(self, url: str | None = None):
        self._use(self.run(self.context.new_page()))
        if url:
            self.open(url)
        return self.page

    def switch_tab(self, index: int | None = None, title: str | None = None, url: str | None = None,
                   timeout: float | None = None):
        """Make another tab the current one: by index, or the first whose title/url *contains*
        the text (waits for it). Returns the tab."""
        if index is not None:
            return self._use(self.tabs[index])

        def _match():
            for p in self.tabs:
                if url and url in p.url:
                    return p
                if title:
                    try:
                        if title in self.run(p.title(), 3):
                            return p
                    except Exception:  # noqa: BLE001 - a tab that does not answer is not the one
                        continue
            return None

        return self._use(self.wait_until(_match, timeout, f"tab title~{title} url~{url}"))

    def wait_new_tab(self, before: list, timeout: float | None = None, switch: bool = True):
        """``before = web.tabs; web.click(link); web.wait_new_tab(before)``"""
        new = self.wait_until(lambda: [p for p in self.tabs if p not in before], timeout, "new tab/window")
        if switch:
            self._use(new[0])
        return new[0]

    def close_tab(self, switch_to: int = -1) -> None:
        self.run(self.page.close())
        if self.tabs:
            self._use(self.tabs[switch_to])

    # -- frames ----------------------------------------------------------------
    @contextlib.contextmanager
    def frame(self, loc):
        """Work inside an iframe, then return to the page::

            with web.frame("#editor-frame"):
                web.type("#body", "hello")
        """
        frame = self.run(self.find(loc).content_frame())
        if frame is None:
            raise LookupError(f"{loc} is not an iframe")
        self._frames.append(frame)
        try:
            yield self
        finally:
            self._frames.remove(frame)

    # -- JS dialogs (alert / confirm / prompt / beforeunload) -------------------
    @contextlib.contextmanager
    def dialog(self, accept: bool = True, prompt_text: str | None = None, timeout: float | None = None,
               required: bool = True):
        """Answer the JavaScript dialogs the block opens - say how BEFORE the action, because an
        open dialog blocks the page::

            with web.dialog(accept=True, prompt_text="Ann") as d:
                web.click("#prompt")
            assert d.text == "Your name?"

        ``accept=False`` presses Cancel. Leaving the block waits for the dialog (TimeoutError
        when none showed; ``required=False``: do not wait). ``d.text`` / ``d.type`` /
        ``d.messages`` tell what was shown. Outside such a block a dialog is dismissed at once
        and kept in ``web.dialogs``."""
        plan = DialogPlan(accept, prompt_text)
        self._dialog_plans.append(plan)
        try:
            yield plan
            if required:
                poll(lambda: plan.seen, self._t(timeout), self.interval, "JavaScript dialog")
        finally:
            self._dialog_plans.remove(plan)

    # -- misc ------------------------------------------------------------------
    def cdp(self, cmd: str, params: dict | None = None):
        """Chrome DevTools Protocol command on the current tab, e.g. ``web.cdp("Page.getLayoutMetrics")``."""
        async def _send():
            session = await self.context.new_cdp_session(self.page)
            try:
                return await session.send(cmd, params or {})
            finally:
                await session.detach()
        return self.run(_send(), what=cmd)

    def screenshot(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.screenshot_bytes())
        return path

    def screenshot_bytes(self) -> bytes:
        """PNG of the current tab's viewport."""
        return self.run(self.page.screenshot(timeout=15000), 20, "screenshot")
