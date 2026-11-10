"""Reading page content: text (shadow DOM aware), attributes, state, lists, tables."""
from __future__ import annotations

from sbtest.web.locators import JS_COMPOSED_TEXT, JS_TEXT, Element


class ReaderMixin:
    def text(self, loc) -> str:
        """Visible text of the element, including text rendered inside its shadow root."""
        return (self.js(JS_TEXT, self.find(loc, visible=False)) or "").strip()

    def texts(self, loc, within: Element | None = None) -> list[str]:
        """Texts of all visible matches, in DOM order."""
        return [self.text(el) for el in self.find_all(loc, within=within)]

    def page_text(self) -> str:
        """All visible text of the current page, piercing every shadow root."""
        return self.js(JS_COMPOSED_TEXT, None) or ""

    def attr(self, loc, name: str) -> str | None:
        """An HTML attribute as written in the markup (None when absent). The live state of
        a control (``value``, ``checked``) is a property: ``web.value`` / ``web.prop``."""
        return self.run(self.find(loc, visible=False).get_attribute(name))

    def prop(self, loc, name: str):
        return self.js("return arguments[0][arguments[1]];", self.find(loc, visible=False), name)

    def value(self, loc) -> str:
        return self.prop(loc, "value") or ""

    def exists(self, loc, visible: bool = True) -> bool:
        """Immediate check, no waiting."""
        return bool(self.find_all(loc, visible=visible))

    def is_visible(self, loc) -> bool:
        return self.exists(loc, visible=True)

    def count(self, loc, visible: bool = True) -> int:
        return len(self.find_all(loc, visible=visible))

    def is_enabled(self, loc) -> bool:
        return bool(self.js(
            "const e = arguments[0];"
            "return !(e.disabled === true || e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true');",
            self.find(loc, visible=False)))

    def is_checked(self, loc) -> bool:
        """Works for input checkbox/radio, si-select, si-toggle, aria widgets."""
        return bool(self.js(
            "const e = arguments[0];"
            "if (typeof e.checked === 'boolean') return e.checked;"
            "const a = e.getAttribute('aria-checked') || e.getAttribute('aria-pressed');"
            "if (a !== null) return a === 'true';"
            "return e.hasAttribute('checked');", self.find(loc, visible=False)))

    def table(self, loc) -> list[dict[str, str]]:
        """``<table>`` -> list of {header: cell_text} dicts."""
        return self.js(r"""
            const t = arguments[0];
            const heads = Array.from(t.querySelectorAll('thead th, tr:first-child th')).map(h => h.innerText.trim());
            const rows = Array.from(t.querySelectorAll('tbody tr')).filter(r => r.querySelector('td'));
            return rows.map(r => {
              const cells = Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim());
              const o = {}; cells.forEach((c, i) => o[heads[i] || String(i)] = c); return o;
            });""", self.find(loc))

    def focused(self) -> Element | None:
        """Deepest focused element (follows shadowRoot.activeElement)."""
        return self.js(
            "let a = document.activeElement; while (a && a.shadowRoot && a.shadowRoot.activeElement)"
            " a = a.shadowRoot.activeElement; return a;")

    def same_element(self, a: Element, b: Element) -> bool:
        """True when both handles point at the same DOM node (handles themselves never compare equal)."""
        return bool(self.js("return arguments[0] === arguments[1]", a, b))

    def aria_snapshot(self, loc="body") -> str:
        """The accessibility tree of ``loc`` as YAML (roles, names, states): a short, readable
        picture of what the page offers - the first thing to read when exploring a page."""
        el = self.find(loc, visible=False)
        return self.run(self._aria(el), what="aria snapshot")

    async def _aria(self, el) -> str:
        # ariaSnapshot lives on locators: reach the element through a temporary marker attribute
        await el.evaluate("e => e.setAttribute('data-sbtest-aria', '1')")
        try:
            frame = await el.owner_frame()
            return await frame.locator("[data-sbtest-aria]").first.aria_snapshot()
        finally:
            await el.evaluate("e => e.removeAttribute('data-sbtest-aria')")

    def html(self) -> str:
        """Markup of the current page (light DOM)."""
        return self.run(self.page.content())
