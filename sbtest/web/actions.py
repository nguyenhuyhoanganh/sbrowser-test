"""User actions on web content: click, type, keys, hover, select, drag & drop, scroll, upload.

All methods take a locator (see ``sbtest.web.locators``) or an element, wait for the element,
scroll it into view and retry when the page re-rendered it meanwhile.
"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.async_api import Error as PlaywrightError

from sbtest.utils import log
from sbtest.web.locators import Element

JS_HTML5_DND = r"""
const src = arguments[0], dst = arguments[1];
const dt = new DataTransfer();
const fire = (el, type, x, y) => {
  const r = el.getBoundingClientRect();
  const ev = new DragEvent(type, {bubbles: true, cancelable: true, composed: true, dataTransfer: dt,
    clientX: r.left + r.width / 2 + (x || 0), clientY: r.top + r.height / 2 + (y || 0)});
  el.dispatchEvent(ev);
};
fire(src, 'dragstart'); fire(dst, 'dragenter'); fire(dst, 'dragover'); fire(dst, 'drop'); fire(src, 'dragend');
"""


class Keys:
    """Key names for ``web.press``: ``web.press(Keys.CONTROL, "a")``, ``web.press(Keys.ENTER)``."""
    ENTER = RETURN = "Enter"
    ESCAPE = "Escape"
    TAB = "Tab"
    SPACE = "Space"
    BACKSPACE = BACK_SPACE = "Backspace"
    DELETE = "Delete"
    INSERT = "Insert"
    HOME, END, PAGE_UP, PAGE_DOWN = "Home", "End", "PageUp", "PageDown"
    UP = ARROW_UP = "ArrowUp"
    DOWN = ARROW_DOWN = "ArrowDown"
    LEFT = ARROW_LEFT = "ArrowLeft"
    RIGHT = ARROW_RIGHT = "ArrowRight"
    CONTROL, SHIFT, ALT, COMMAND, META = "Control", "Shift", "Alt", "Meta", "Meta"
    F1, F2, F3, F4, F5, F6 = "F1", "F2", "F3", "F4", "F5", "F6"
    F7, F8, F9, F10, F11, F12 = "F7", "F8", "F9", "F10", "F11", "F12"


MODIFIERS = (Keys.CONTROL, Keys.SHIFT, Keys.ALT, Keys.META)


def key_combos(keys: tuple) -> list[str]:
    """``(Keys.CONTROL, "a")`` -> ``["Control+a"]``; ``("ENTER",)`` -> ``["Enter"]``: the leading
    modifiers are held for every other key. Names of ``Keys`` are accepted in any case."""
    names = [getattr(Keys, k.upper(), k) if isinstance(k, str) and len(k) > 1 else k for k in keys]
    mods = [k for k in names if k in MODIFIERS]
    rest = [k for k in names if k not in MODIFIERS]
    return ["+".join(mods + [k]) for k in rest] or ["+".join(mods)]


class ActionsMixin:
    def _ms(self) -> float:
        return self.action_timeout * 1000

    def _act(self, coro, what: str = ""):
        """Run an action that waits up to ``action_timeout`` by itself."""
        return self.run(coro, self.action_timeout + 10, what)

    def _with_retry(self, loc, fn, attempts: int = 3):
        last = None
        for i in range(attempts):
            el = self.find(loc)
            try:
                return fn(el)
            except PlaywrightError as e:   # detached / re-rendered / covered: look it up again
                last = e
                log.debug("retry %s on %s: %s", i + 1, loc, str(e).splitlines()[0])
                if isinstance(loc, Element):
                    break
                time.sleep(0.3)
        raise last

    def _scroll(self, el: Element) -> None:
        self.js("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", el)

    def scroll_to(self, loc) -> Element:
        el = self.find(loc, visible=False)
        self._scroll(el)
        return el

    def scroll_by(self, dx: int = 0, dy: int = 500) -> None:
        self.js("window.scrollBy(arguments[0], arguments[1]);", dx, dy)

    def click(self, loc, js_fallback: bool = True) -> None:
        """Real click: waits until the element is visible, still and enabled. Falls back to a
        JS click when something stays over it (``js_fallback=False``: raise instead)."""

        async def _click(el: Element):
            try:
                await el.click(timeout=self._ms())
            except PlaywrightError as e:
                if not js_fallback or "not attached" in str(e):
                    raise
                log.debug("JS click fallback on %s: %s", loc, str(e).splitlines()[0])
                await el.evaluate("e => e.click()")

        def _do(el: Element):
            self._scroll(el)
            self._mark("click", el)
            self._act(_click(el), f"click {loc}")

        self._with_retry(loc, _do)

    def js_click(self, loc) -> None:
        el = self.find(loc, visible=False)
        self._mark("click", el)
        self.js("arguments[0].click();", el)

    def double_click(self, loc) -> None:
        def _double(el):
            self._mark("double-click", self.scroll_to(el))
            self._act(el.dblclick(timeout=self._ms()))

        self._with_retry(loc, _double)

    def right_click(self, loc) -> None:
        """Opens the *web* context menu (si-action-menu etc.). Native context menus: use native.context_menu_web."""
        def _right(el):
            self._mark("right-click", self.scroll_to(el))
            self._act(el.click(button="right", timeout=self._ms()))

        self._with_retry(loc, _right)

    def hover(self, loc) -> None:
        def _hover(el):
            self._mark("hover", self.scroll_to(el))
            self._act(el.hover(timeout=self._ms()))

        self._with_retry(loc, _hover)

    def type(self, loc, text: str, clear: bool = True, enter: bool = False) -> None:
        """Type into an input, key by key. For a component that wraps its input (``si-input``)
        target the inner ``input``: ``"si-input#name >>> #input"``."""

        async def _type(el: Element):
            try:
                await el.click(timeout=self._ms())
            except PlaywrightError:   # covered or not clickable: focus is enough to type
                pass
            await el.focus()
            if clear:
                await self._clear(el)
            await self.page.keyboard.type(text)
            if enter:
                await self.page.keyboard.press("Enter")

        def _do(el: Element):
            self._scroll(el)
            self._mark("type", el, repr(text))
            self._act(_type(el), f"type into {loc}")

        self._with_retry(loc, _do)

    async def _clear(self, el: Element) -> None:
        try:
            await el.fill("", timeout=1000)
        except PlaywrightError:   # not an input / textarea / contenteditable: select all + Delete
            await el.press("Control+a")
            await el.press("Delete")

    def clear(self, loc) -> None:
        self._with_retry(loc, lambda el: self._act(self._clear(el)))

    def set_value(self, loc, value: str) -> None:
        """Set value via JS + input/change events (for inputs that ignore typing)."""
        el = self.find(loc, visible=False)
        self._mark("type", el, repr(value))
        self.js(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true, composed: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true, composed: true}));", el, value)

    def press(self, *keys, loc=None) -> None:
        """Send keys to an element or to the focused element.

        ``web.press(Keys.ENTER)``  ``web.press(Keys.CONTROL, "a")`` (chord)  ``web.press("Delete")``
        Keys sent here go to the *page*; browser shortcuts (Ctrl+D, Ctrl+H, Ctrl+T...) are
        handled by the browser UI - use ``native.hotkey("^d")`` for those.
        """
        combos = key_combos(keys)
        if loc is not None:
            el = self.find(loc)
            self._mark("keys", el)
            for combo in combos:
                self._act(el.press(combo, timeout=self._ms()))
            return
        for combo in combos:
            self.run(self.page.keyboard.press(combo))

    def type_keys(self, text: str, enter: bool = False) -> None:
        """Type ``text`` into the element that has the focus (a field the page focused by
        itself, e.g. a new folder's name). ``text`` is typed as is - never read as a key name."""
        self._mark("type", self.focused(), repr(text))
        self.run(self.page.keyboard.type(text))
        if enter:
            self.run(self.page.keyboard.press("Enter"))

    def select(self, loc, text: str | None = None, value: str | None = None, index: int | None = None) -> None:
        """Native ``<select>``. For a component wrapping a select target the inner select."""
        el = self.find(loc)
        self._mark("select", el, text or value or (str(index) if index is not None else ""))
        if text is not None:
            self._act(el.select_option(label=text, timeout=self._ms()))
        elif value is not None:
            self._act(el.select_option(value=value, timeout=self._ms()))
        elif index is not None:
            self._act(el.select_option(index=index, timeout=self._ms()))

    def set_checked(self, loc, checked: bool = True) -> None:
        """Checkbox / si-select / si-toggle: click only if the state differs."""
        el = self.find(loc)
        if self.is_checked(el) != checked:
            self.click(el)
            self.wait_until(lambda: self.is_checked(el) == checked, message=f"checked={checked} {loc}")

    def _center(self, el: Element, offset: tuple[int, int] = (0, 0)) -> tuple[float, float]:
        box = self.run(el.bounding_box())
        if not box:
            raise LookupError("element has no box on the page (hidden?)")
        return box["x"] + box["width"] / 2 + offset[0], box["y"] + box["height"] / 2 + offset[1]

    async def _mouse_drag(self, start, end) -> None:
        mouse = self.page.mouse
        await mouse.move(*start)
        await mouse.down()
        await mouse.move(start[0] + 5, start[1] + 5, steps=2)
        await mouse.move(*end, steps=12)
        await mouse.up()

    def drag_and_drop(self, source, target, method: str = "actions", offset: tuple[int, int] = (0, 0)) -> None:
        """Drag ``source`` onto ``target``.

        method:
          "actions" mouse press / move / release sent to the page (mouse-event based DnD, sortable
                    lists, and HTML5 drags the browser starts from them)
          "html5"   synthesized HTML5 DragEvents (pages using draggable=true / dataTransfer)
          "native"  real OS mouse via pywinauto (anything, incl. drop on browser UI) - needs native
        """
        src, dst = self.scroll_to(source), self.find(target)
        if method != "native":   # the native drag records its own screen points
            self._mark("drag", src)
            self._mark("drop", dst)
        if method == "html5":
            self.js(JS_HTML5_DND, src, dst)
        elif method == "actions":
            self.run(self._mouse_drag(self._center(src), self._center(dst, offset)))
        elif method == "native":
            if self.native is None:
                raise RuntimeError("native drag requires the native layer (Windows, non-headless)")
            self.native.drag_web_element(self, src, dst, offset)
        else:
            raise ValueError(method)

    def drag_by(self, source, dx: int, dy: int) -> None:
        x, y = self._center(self.scroll_to(source))
        self.run(self._mouse_drag((x, y), (x + dx, y + dy)))

    def upload(self, loc, *files: str | Path) -> None:
        """Set files on ``<input type=file>`` without opening the OS file picker.
        If the page only opens a picker from a button, use ``native.file_dialog().open(path)``."""
        el = self.find(loc, visible=False)
        self._mark("upload", el, ", ".join(Path(f).name for f in files))
        self._act(el.set_input_files([str(Path(f).resolve()) for f in files], timeout=self._ms()))
