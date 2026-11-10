"""``Web``: the single object tests use for everything inside web content.

    web.open_internal("bookmarks")
    web.type("bookmarks-app >>> #searchInput", "abc")
    web.click("text=Delete")
    assert "deleted" in web.text("si-snack-bar")

Built on Playwright, attached to the browser the session started. ``web.page`` is the
Playwright page of the current tab and ``web.context`` its browser context, for the rare case
a test needs Playwright itself: run their (async) calls with ``web.run(web.page.pdf())``.
"""
from __future__ import annotations

import threading

from playwright.async_api import ElementHandle

from sbtest import steps
from sbtest.browser.runtime import runtime
from sbtest.utils import log
from sbtest.web.actions import ActionsMixin
from sbtest.web.navigation import NavigationMixin
from sbtest.web.reader import ReaderMixin
from sbtest.web.waits import WaitsMixin

# Runs a script written like a function body ("return arguments[0].value") and says whether
# the result holds DOM nodes: those come back as element handles, everything else as JSON.
_JS_CALL = """async (__args) => {
  const __v = await (function() {
%s
  }).apply(null, __args);
  const isNode = x => !!x && typeof x === 'object' && typeof x.nodeType === 'number' && typeof x.nodeName === 'string';
  if (isNode(__v) || (Array.isArray(__v) && __v.some(isNode))) { window.__sbtest_ret = __v; return {node: true}; }
  return {value: __v};
}"""
_JS_TAKE = "() => { const v = window.__sbtest_ret; delete window.__sbtest_ret; return v; }"
MAX_CONSOLE_LINES = 500


class Web(WaitsMixin, ActionsMixin, ReaderMixin, NavigationMixin):
    def __init__(self, context, page, cfg, native_factory=None, new_window=None, recover=None,
                 home_url: str = "") -> None:
        self.rt = runtime()
        self.context = context
        self._page = page
        #: ``new_window(url)`` -> Playwright page of a new browser window opened on ``url``.
        #: The browser starts without a window: the first ``open`` makes it on its page.
        self._new_window = new_window
        #: ``recover(page)`` -> the page again after Playwright lost a tab that is still open
        #: (Samsung cuts DevTools off a tab leaving its home page), None when nothing was lost
        self._recover = recover
        #: the browser's home page: a window the test did not open on a page shows it
        self.home_url = home_url
        self.cfg = cfg
        self._native_factory = native_factory
        self._frames: list = []
        self.timeout = float(cfg.get("timeouts.default", 10))
        self.long_timeout = float(cfg.get("timeouts.long", 30))
        self.interval = float(cfg.get("timeouts.poll", 0.2))
        #: seconds a click / typing waits for its element to be ready before the fallback
        self.action_timeout = float(cfg.get("timeouts.action", 5))
        self.page_load_timeout = float(cfg.get("timeouts.page_load", 30))
        #: seconds any single browser command may take (a blocked page raises TimeoutError)
        self.command_timeout = float(cfg.get("timeouts.command", 30))
        #: (locator text, element or None) of the last element looked up - used by failure reports
        self.last_target: tuple[str, object] | None = None
        #: URL the browser window was opened on (browser.start_page); the first open()
        #: of exactly that URL does not load it again
        self.preloaded_url = ""
        #: every JavaScript dialog seen: {type, message, answer, expected}
        self.dialogs: list[dict] = []
        self._dialog_plans: list = []
        #: console errors / warnings and uncaught page errors of every tab (failure evidence)
        self.console: list[str] = []
        self.run(self._listen())

    # -- Playwright plumbing ---------------------------------------------------------
    def run(self, coro, timeout: float | None = None, what: str = ""):
        """Run a Playwright coroutine and return its result (TimeoutError after ``timeout`` s)."""
        return self.rt.run(coro, self.command_timeout if timeout is None else timeout, what)

    @property
    def page(self):
        """Playwright page of the current tab (``switch_tab`` / ``wait_new_tab`` change it).
        Before the first ``open`` the browser has no window: using the page opens one on the
        home page."""
        if threading.current_thread() is self.rt._thread:
            return self._page          # inside a Playwright call: never open or reconnect here
        self._find_lost()
        self._drop_closed()
        if self._page is None and self._new_window is not None:
            self._page = self._new_window(self.home_url or "about:blank")
        return self._page

    @page.setter
    def page(self, value) -> None:
        self._page = value

    def _find_lost(self) -> None:
        """Reconnect when Playwright lost a tab that is still open, and keep the current one."""
        if self._recover is None:
            return
        cur = self._page
        new = self._recover(cur)
        if new is not None and cur is not None and cur.is_closed():
            self._page = new
            self._frames.clear()

    def rebind(self, context) -> None:
        """Go on with the browser context of a new connection (``session.recover``)."""
        self.context = context
        self.run(self._listen())

    def is_home(self, page=None) -> bool:
        """True when the tab (default: the current one) shows the browser's home page."""
        page = page if page is not None else self._page
        url = page.url if page is not None else ""
        return url.startswith(("chrome://new-tab-page", "chrome://newtab", "internet://newtab"))

    @property
    def has_window(self) -> bool:
        """False while the browser has no window (nothing opened since the start, or every
        window was closed)."""
        self._drop_closed()
        return self._page is not None

    def _drop_closed(self) -> None:
        """Every window was closed (the current tab with them): back to "no window" - the next
        page opens a new one, like a user starting the browser again."""
        if self._page is None or not self._page.is_closed() or self.context.pages:
            return
        if threading.current_thread() is self.rt._thread:
            return
        self._find_lost()           # a tab that left the home page is not closed: find it first
        if self._page is not None and self._page.is_closed() and not self.context.pages:
            self._page = None
            self._frames.clear()

    @property
    def root(self):
        """Where locators are searched: the current tab, or the iframe of ``with web.frame(...)``."""
        return self._frames[-1] if self._frames else self.page

    async def _listen(self) -> None:
        self.context.on("dialog", self._on_dialog)
        self.context.on("console", self._on_console)
        self.context.on("weberror", lambda e: self._log_console(f"[pageerror] {e.error}"))

    def _log_console(self, line: str) -> None:
        if len(self.console) < MAX_CONSOLE_LINES:
            self.console.append(" ".join(line.split())[:500])

    def _on_console(self, msg) -> None:
        if msg.type in ("error", "warning"):
            where = msg.location or {}
            self._log_console(f"[{msg.type}] {msg.text}  ({where.get('url', '')}:{where.get('lineNumber', '')})")

    async def _on_dialog(self, dialog) -> None:
        """Answer a JavaScript dialog at once (an open one blocks the page and every command):
        as the running ``with web.dialog(...)`` says, else dismiss it (leave the page for a
        "Leave site?" dialog) and keep it in ``web.dialogs``."""
        plan = self._dialog_plans[-1] if self._dialog_plans else None
        accept = plan.accept if plan else dialog.type == "beforeunload"
        rec = {"type": dialog.type, "message": dialog.message, "answer": "accept" if accept else "dismiss",
               "expected": plan is not None}
        self.dialogs.append(rec)
        if plan is not None:
            plan.seen.append(rec)
        else:
            log.warning("unexpected JavaScript %s %r: %sed", dialog.type, dialog.message, rec["answer"])
        try:
            if accept:
                await dialog.accept(plan.prompt_text if plan and plan.prompt_text is not None else "")
            else:
                await dialog.dismiss()
        except Exception as e:  # noqa: BLE001 - the page closed meanwhile
            log.debug("dialog answer failed: %s", e)

    # -- JavaScript --------------------------------------------------------------------
    def js(self, script: str, *args):
        """Run JavaScript written as a function body in the page (or current iframe):
        ``web.js("return arguments[0].value", el)``. Arguments: JSON values and elements.
        Returns JSON; a DOM node comes back as an element, an array of nodes as a list of
        elements. A returned Promise is awaited."""
        return self.run(self._js(self.root, script, args), what="JavaScript")

    async def _js(self, root, script: str, args: tuple):
        out = await root.evaluate(_JS_CALL % script, list(args))
        if not out.get("node"):
            return out.get("value")
        handle = await root.evaluate_handle(_JS_TAKE)
        el = handle.as_element()
        if el is not None:
            return el
        props = await handle.get_properties()
        items = [props[k] for k in sorted((k for k in props if k.isdigit()), key=int)]
        return [p.as_element() or await p.json_value() for p in items]

    # -- evidence ------------------------------------------------------------------------
    def highlight(self, el=None, color: str = "red") -> bool:
        """Outline an element (default: the last one used) so it shows in a screenshot."""
        el = el if el is not None else (self.last_target[1] if self.last_target else None)
        if not isinstance(el, ElementHandle):
            return False
        try:
            self.js("const e = arguments[0]; e.scrollIntoView({block: 'center'});"
                    "e.style.outline = '3px solid ' + arguments[1]; e.style.outlineOffset = '2px';", el, color)
            return True
        except Exception:  # noqa: BLE001 - detached element
            return False

    def _mark(self, kind: str, el, label: str = "") -> None:
        """Record where this action happens, for the step screenshot (only when recording)."""
        if not steps.recording() or el is None:
            return
        try:
            rect = self.js("const r = arguments[0].getBoundingClientRect();"
                           "return [r.left, r.top, r.width, r.height, window.devicePixelRatio];", el)
            steps.mark(kind, label, web=tuple(rect))
        except Exception:  # noqa: BLE001 - only a picture aid
            pass

    @property
    def native(self):
        """The session's NativeBrowser (created on first use), or None when native is disabled."""
        return self._native_factory() if self._native_factory else None
