"""One locator syntax for everything, including Shadow DOM (all internal pages use it).

A locator is a string with an optional prefix; it is turned into a Playwright selector:

    "#id .class"                      CSS (default). CSS pierces open shadow roots.
    "css=button.primary"              CSS
    "xpath=//div[@id='x']"            XPath (also any string starting with "/" or "("); light DOM only
    "id=search"  "name=q"             by id / name attribute
    "bookmarks-app >>> #searchInput"  path: each ">>>" continues inside the element matched so
                                      far, its shadow root included ("deep=" prefix optional)
    "deepcss=si-snack-bar"            same as plain CSS (kept: it says "anywhere, any shadow root")
    "text=Delete"                     smallest element whose text is exactly "Delete"
    "text~=Deleted"                   element whose text contains "Deleted" (case-insensitive)
    "aria=Search bookmarks"           element whose aria-label / title / placeholder equals it
    "role=button[name=\"Save\"]"      Playwright role selector (accessible role + name)
    "pw=<selector>"                   any other Playwright selector, passed through as is

Every API that takes a locator also accepts an element (a Playwright ``ElementHandle``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.async_api import ElementHandle

#: what ``web.find`` returns and every ``web.*`` method accepts in place of a locator
Element = ElementHandle

# ---------------------------------------------------------------- shadow-aware JS
_JS_COMMON = r"""
const scopeOf = (n) => (n && n.shadowRoot) ? n.shadowRoot : n;
const SKIP = new Set(['SCRIPT', 'STYLE', 'TEMPLATE', 'NOSCRIPT']);
const visible = (el) => {
  if (!(el instanceof Element)) return false;
  const st = getComputedStyle(el);
  if (st.visibility === 'hidden' || st.display === 'none') return false;
  return el.getClientRects().length > 0;
};
"""

# composed (shadow-including) visible text of an element or the whole page
JS_COMPOSED_TEXT = _JS_COMMON + r"""
const root = arguments[0] || document.body;
const kids = (n) => {
  if (n.shadowRoot) return Array.from(n.shadowRoot.childNodes);
  if (n.tagName === 'SLOT') { const a = n.assignedNodes({flatten: true}); return a.length ? a : Array.from(n.childNodes); }
  return Array.from(n.childNodes);
};
const parts = [];
const visit = (n) => {
  if (n.nodeType === 3) { parts.push(n.nodeValue); return; }
  if (n.nodeType === 1) {
    if (SKIP.has(n.tagName)) return;
    const st = getComputedStyle(n);
    if (st.display === 'none' || st.visibility === 'hidden') return;
    if (n.tagName === 'INPUT' || n.tagName === 'TEXTAREA') { parts.push(' ' + (n.value || '') + ' '); return; }
  }
  const block = n.nodeType === 1 && st_block(n);
  if (block) parts.push('\n');
  for (const c of kids(n)) visit(c);
  if (block) parts.push('\n');
};
const st_block = (el) => { const d = getComputedStyle(el).display; return d && !d.startsWith('inline'); };
visit(root);
return parts.join('').replace(/[ \t\r\f\v]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{2,}/g, '\n').trim();
"""



# what a person reads in the element: innerText when it has no shadow root, else the composed text
JS_TEXT = (
    "const e0 = arguments[0];"
    "if (e0 && !e0.shadowRoot && typeof e0.innerText === 'string') { const t = e0.innerText.trim(); if (t) return t; }\n"
    + JS_COMPOSED_TEXT)


@dataclass(frozen=True)
class Locator:
    kind: str  # css | xpath | id | name | deep | deepcss | text | textc | aria | role | pw
    value: str | tuple

    def __str__(self) -> str:
        return f"{self.kind}={self.value}"


_PREFIXES = (("text~=", "textc"), ("text=", "text"), ("aria=", "aria"), ("deepcss=", "deepcss"), ("deep=", "deep"),
             ("css=", "css"), ("xpath=", "xpath"), ("id=", "id"), ("name=", "name"), ("role=", "role"), ("pw=", "pw"))


def parse(spec) -> Locator:
    """Turn a locator string into a :class:`Locator`."""
    if isinstance(spec, Locator):
        return spec
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError(f"Bad locator: {spec!r}")
    s = spec.strip()
    for prefix, kind in _PREFIXES:
        if s.startswith(prefix):
            value = s[len(prefix):]
            if kind == "css" and ">>>" in value:
                kind = "deep"
            if kind == "deep":
                return Locator("deep", tuple(p.strip() for p in value.split(">>>") if p.strip()))
            return Locator(kind, value)
    if s.startswith("/") or s.startswith("("):
        return Locator("xpath", s)
    if ">>>" in s:
        return Locator("deep", tuple(p.strip() for p in s.split(">>>") if p.strip()))
    return Locator("css", s)


def _quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_selector(spec, visible: bool = False) -> str:
    """The Playwright selector of a locator; ``visible`` keeps only elements shown on the page."""
    loc = parse(spec)
    v = loc.value
    if loc.kind in ("css", "deepcss"):
        sel = f"css={v}"
    elif loc.kind == "deep":
        sel = " >> ".join(f"css={seg}" for seg in v)
    elif loc.kind == "xpath":
        sel = f"xpath={v}"
    elif loc.kind in ("id", "name"):
        sel = f"css=[{loc.kind}={_quoted(v)}]"
    elif loc.kind == "text":
        sel = f"text={_quoted(v)}"
    elif loc.kind == "textc":
        sel = "text=/" + re.sub(r"([.*+?^${}()|\[\]\\/])", r"\\\1", v) + "/i"
    elif loc.kind == "aria":
        sel = "css=" + ", ".join(f"[{a}={_quoted(v)}]" for a in ("aria-label", "title", "placeholder", "label"))
    elif loc.kind == "role":
        sel = f"role={v}"
    elif loc.kind == "pw":
        sel = v
    else:
        raise ValueError(f"Unknown locator kind: {loc.kind}")
    return sel + (" >> visible=true" if visible else "")


async def find_all(root, spec, within: Element | None = None, visible: bool = False) -> list[Element]:
    """All elements matching ``spec`` right now (no waiting), in document order. ``root`` is
    the page or frame; ``within`` scopes the search to an element (its shadow root included)."""
    if isinstance(spec, ElementHandle):
        return [spec]
    return await (within if within is not None else root).query_selector_all(to_selector(spec, visible))
