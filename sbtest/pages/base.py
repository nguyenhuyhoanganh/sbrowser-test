"""BasePage: helpers shared by every page object - Samsung's own WebUI components (si-*).

Samsung rewrote the internal pages with its own component set; compared with upstream Chromium:

    Chromium (cr-*)               Samsung (si-*)
    cr-toolbar-search-field       si-side-bar-toolbar-search-field (left side bar)
    cr-button in toolbar          si-toolbar-button (label in aria-label of its #container)
    cr-toast                      si-snack-bar inside si-snack-bar-manager (+ si-flat-button "Undo")
    cr-dialog                     si-dialog (wraps a native <dialog>), buttons dialog-button-si
    cr-action-menu .dropdown-item si-action-menu, button.si-context-menu-item[role=menuitem]
    cr-checkbox per row           si-select (round check box at the start of each row)
    cr-toggle                     si-toggle

STATUS: verified on Samsung Browser 31.0.1.40 (Chromium 151) with the Selenium web layer;
ported to Playwright since and not run on a Samsung build yet - run the feature before trusting it.
"""
from __future__ import annotations


from sbtest.web import Element
from sbtest.web.web import Web


def q(value: str) -> str:
    """Quote a value for a CSS attribute selector: ``f'[aria-label={q(name)}]'``."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


_JS_VISIBLE_BY_TEXT = r"""
const sel = arguments[0], text = arguments[1], contains = arguments[2], start = arguments[3];
const out = [];
const norm = s => (s || '').replace(/\s+/g, ' ').trim();
// text as rendered, including shadow content and slotted nodes
const ctext = n => {
  if (n.nodeType === 3) return n.nodeValue;
  if (n.nodeType !== 1 && n.nodeType !== 11) return '';
  if (n.nodeType === 1 && /^(SCRIPT|STYLE|TEMPLATE)$/.test(n.tagName)) return '';
  let kids = n.shadowRoot ? n.shadowRoot.childNodes : n.childNodes;
  if (n.tagName === 'SLOT') { const a = n.assignedNodes({flatten: true}); if (a.length) kids = a; }
  let t = ''; for (const c of kids) t += ' ' + ctext(c); return t;
};
const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
const walk = root => {
  for (const el of root.querySelectorAll(sel)) {
    const t = norm(el.shadowRoot ? ctext(el) : (el.innerText || el.textContent));
    if ((contains ? t.includes(text) : t === text) && vis(el)) out.push(el);
  }
  for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
};
walk(start ? (start.shadowRoot || start) : document);
return out;
"""

_JS_SNACKBAR_TEXT = r"""
const out = [];
// text as shown: through shadow roots and slots, without <style> / <script> content
const text = n => {
  if (n.nodeType === 3) return n.nodeValue;
  if (n.nodeType !== 1 && n.nodeType !== 11) return '';
  if (n.nodeType === 1 && /^(STYLE|SCRIPT|TEMPLATE)$/.test(n.tagName)) return '';
  let kids = n.shadowRoot ? n.shadowRoot.childNodes : n.childNodes;
  if (n.tagName === 'SLOT') { const a = n.assignedNodes({flatten: true}); if (a.length) kids = a; }
  let t = ''; for (const c of kids) t += ' ' + text(c); return t;
};
const walk = root => {
  for (const m of root.querySelectorAll('si-snack-bar-manager')) {
    const bar = m.shadowRoot && m.shadowRoot.querySelector('si-snack-bar');
    const shown = bar && (bar.hasAttribute('open') || bar.open || getComputedStyle(bar).display !== 'none'
                          && bar.getClientRects().length > 0);
    if (shown) out.push(text(m.shadowRoot).replace(/\s+/g, ' ').trim());
  }
  for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
};
walk(document);
return out.filter(Boolean).join(' | ');
"""

_JS_OPEN_SI_DIALOG = r"""
const found = [];
const walk = root => {
  for (const d of root.querySelectorAll('si-dialog')) {
    const inner = d.shadowRoot && d.shadowRoot.querySelector('dialog');
    if ((inner && inner.open) || d.hasAttribute('open')) found.push(d);
  }
  for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
};
walk(document);
return found[0] || null;
"""


class BasePage:
    """Base of every page object. A page object adds its selectors (class constants) and
    one method per user action; this class holds what every Samsung internal page shares:
    open/wait, side bar search and filters, toolbar buttons, menus, snack bar, si-dialog.

    Layout of every page object (keep it when adding a method):
    selectors -> read (returns data, changes nothing) -> wait -> actions (one per user action,
    docstring = the UI path and what it returns). No assertions: return data, wait for the
    action's own effect."""

    # -- selectors -----------------------------------------------------------------
    #: key in config ``pages`` (bookmarks, history, ...)
    page: str = ""
    #: element that proves the page rendered
    ROOT: str = "body"
    #: host element of the page toolbar (si-toolbar-button children)
    TOOLBAR = "body"
    SEARCH_INPUT = "deepcss=si-side-bar-toolbar-search-field"
    SIDE_BAR_ITEM = "deepcss=.si-nav-menu-item"
    MENU_ITEM = "deepcss=button.si-context-menu-item"
    TOAST = "deepcss=si-snack-bar"
    DIALOG_BUTTON = "dialog-button-si, si-flat-button, button"

    def __init__(self, web: Web) -> None:
        self.web = web

    # -- open ----------------------------------------------------------------------
    @property
    def url(self) -> str:
        return self.web.cfg.page_url(self.page)

    def open(self, subpath: str = "") -> "BasePage":
        """Open the page (``subpath``: e.g. ``shortcuts``) and wait until it rendered."""
        self.web.open(self.url + (("/" + subpath.lstrip("/")) if subpath else ""))
        self.wait_loaded()
        return self

    def wait_loaded(self) -> None:
        try:
            self.web.wait_present(self.ROOT, timeout=self.web.long_timeout)
        except TimeoutError as e:
            raise TimeoutError(
                f"{type(self).__name__} did not render at {self.web.url!r} (expected {self.url}): {e}. "
                "If the URL is wrong check config pages.scheme / pages.<name>; if the page loaded, "
                f"ROOT={self.ROOT!r} no longer matches - re-explore with `python -m sbtest.tools.dom {self.page}`."
            ) from e

    def is_open(self) -> bool:
        return self.web.url.startswith(self.url)

    # -- find by text ------------------------------------------------------------------
    def find_by_text(self, css: str, text: str, contains: bool = False, within: Element | None = None,
                     timeout: float | None = None) -> Element:
        """Visible element of ``css`` (searched in all shadow roots) whose text is ``text``."""
        return self.web.wait_until(
            lambda: (self.web.js(_JS_VISIBLE_BY_TEXT, css, text, contains, within) or [None])[0],
            timeout, f"{css} with text {text!r}")

    def click_text(self, text: str, css: str = "button, cr-button, a, [role=button], [role=menuitem], .dropdown-item",
                   contains: bool = False, within: Element | None = None) -> None:
        self.web.click(self.find_by_text(css, text, contains, within))

    # -- side bar: search and filters ---------------------------------------------------
    def search(self, text: str) -> None:
        """Type in the side bar search field (results are debounced: wait on the list)."""
        field = self.web.find(self.SEARCH_INPUT)
        self.web.type(self.web.find("deep=#searchInput", within=field), text)

    def clear_search(self) -> None:
        field = self.web.find(self.SEARCH_INPUT)
        inp = self.web.find("deep=#searchInput", within=field)
        self.web.clear(inp)
        self.web.set_value(inp, "")

    def side_bar(self, text: str) -> None:
        """Click an entry of the left side bar (filters such as ``Last hour``, ``Image``...).
        Matched on the light-DOM text: si-select repeats its label in a shadow aria node."""
        def _find():
            for el in self.web.find_all(self.SIDE_BAR_ITEM):
                if self.web.js("return (arguments[0].textContent || '').replace(/\\s+/g, ' ').trim()", el) == text:
                    return el
            return None
        self.web.click(self.web.wait_until(_find, message=f"side bar entry {text!r}"))

    # -- toolbar (si-toolbar-button) ------------------------------------------------------
    def toolbar_button(self, label: str) -> Element:
        """Toolbar button by its label (``Edit``, ``Delete``, ``Create folder``, ``Load Unpacked``...)."""
        return self.web.find(f"deepcss=[role=button][aria-label={q(label)}]", within=self.web.find(self.TOOLBAR))

    def toolbar_labels(self) -> list[str]:
        """Labels of the toolbar buttons shown now (they change with the selection)."""
        return [self.web.attr(e, "aria-label")
                for e in self.web.find_all("deepcss=[role=button][aria-label]", within=self.web.find(self.TOOLBAR))]

    def toolbar_enabled(self, label: str) -> bool:
        host = self.web.js("return arguments[0].getRootNode().host", self.toolbar_button(label))
        return not self.web.js("return arguments[0].hasAttribute('disabled')", host)

    def toolbar(self, label: str) -> None:
        """Click a toolbar button by its label."""
        self.web.click(self.toolbar_button(label))

    def toolbar_any(self, *labels: str) -> str:
        """Click the first toolbar button present among ``labels`` (labels change with the
        selection, e.g. "Delete" / "Delete all"); returns the label used."""
        for label in labels:
            if self.web.find_all(f"deepcss=[role=button][aria-label={q(label)}]", within=self.web.find(self.TOOLBAR)):
                self.toolbar(label)
                return label
        raise LookupError(f"none of the toolbar buttons {labels}")

    def cancel_selection(self) -> None:
        """The "<" (Cancel) button of the selection toolbar ("2 selected")."""
        self.web.click(self.web.find("deepcss=#back-icon-button", within=self.web.find(self.TOOLBAR)))

    # -- menus (si-action-menu: right click on a row, ⋮ buttons) ---------------------------
    def menu_items(self) -> list[str]:
        """Labels of the open menu."""
        return [t for t in (self.web.text(e) for e in self.web.find_all(self.MENU_ITEM)) if t]

    def click_menu_item(self, text: str) -> None:
        """Click an item of the open menu by its exact label."""
        self.web.click(self.find_by_text("button.si-context-menu-item, [role=menuitem]", text))

    def choose_menu_item(self, action: str, menu: str = "menu") -> str:
        """Wait for the open menu, click ``action`` - exact label, else the first label that
        starts with it (``Open all`` -> "Open all (2) in new tab"). Returns the label clicked."""
        items = self.web.wait_until(lambda: self.menu_items() or None, message=f"{menu} open")
        match = next((i for i in items if i == action), None) or next((i for i in items if i.startswith(action)), None)
        if match is None:
            raise LookupError(f"{action!r} not in {menu} {items}")
        self.click_menu_item(match)
        return match

    # -- snack bar (si-snack-bar: "1 bookmark deleted" [Undo]) ------------------------------
    def toast_element(self) -> Element | None:
        """The snack bar shown now, or None."""
        for t in self.web.find_all(self.TOAST, visible=True):
            return t
        return None

    def wait_toast(self, contains: str = "", timeout: float | None = None) -> str:
        """Wait for the snack bar ("1 bookmark deleted"...) and return its text."""
        def _t():
            txt = self.web.js(_JS_SNACKBAR_TEXT)
            return txt if txt and contains.lower() in txt.lower() else None
        return self.web.wait_until(_t, timeout, f"snack bar containing {contains!r}")

    def toast_action(self, text: str = "Undo") -> None:
        """Click the snack bar's button (``Undo``)."""
        self.click_text(text, css="si-flat-button, button")

    # -- dialogs (si-dialog) -------------------------------------------------------------
    def has_dialog(self) -> bool:
        return bool(self.web.js(_JS_OPEN_SI_DIALOG))

    def open_dialog(self, timeout: float | None = None) -> Element:
        """Wait for an open si-dialog and return it."""
        return self.web.wait_until(lambda: self.web.js(_JS_OPEN_SI_DIALOG), timeout, "open si-dialog")

    def dialog_text(self) -> str:
        return self.web.js("return (arguments[0].innerText || arguments[0].textContent || '').trim()",
                           self.open_dialog())

    def dialog_input(self, input_id: str) -> Element:
        """Inner <input> of an si-input in the open dialog, e.g. ``dialog_input("name")``."""
        return self.web.find(f"deep=#{input_id} >>> #input", within=self._dialog_host())

    def dialog_button(self, text: str) -> None:
        """Click a button of the open dialog by its label."""
        self.click_text(text, css=self.DIALOG_BUTTON, within=self._dialog_host())

    def wait_dialog_closed(self, timeout: float | None = None) -> None:
        self.web.wait_until(lambda: not self.has_dialog(), timeout, "si-dialog closed")

    def answer_dialog_if_open(self, confirm: bool, confirm_labels: tuple[str, ...],
                              cancel_label: str = "Cancel", wait: float = 1.5) -> str | None:
        """A confirmation that may or may not show: confirm with the first of ``confirm_labels``
        present, or cancel. Returns the label clicked, None when no dialog showed."""
        if confirm:
            return self.confirm_dialog_if_open(*confirm_labels, wait=wait)
        try:
            self.open_dialog(timeout=wait)
        except TimeoutError:
            return None
        self.dialog_button(cancel_label)
        self.wait_dialog_closed()
        return cancel_label

    def confirm_dialog_if_open(self, *labels: str, wait: float = 1.5) -> str | None:
        """Click the first of ``labels`` if a confirmation si-dialog shows up within ``wait`` s."""
        try:
            self.open_dialog(timeout=wait)
        except TimeoutError:
            return None
        for label in labels:
            try:
                self.find_by_text(self.DIALOG_BUTTON, label, within=self._dialog_host(), timeout=0.5)
            except TimeoutError:
                continue
            self.dialog_button(label)
            self.wait_dialog_closed()
            return label
        raise LookupError(f"none of {labels} in dialog: {self.dialog_text()!r}")

    def _dialog_host(self) -> Element:
        """Component that owns the open si-dialog (its inputs/buttons live in the same shadow root)."""
        return self.web.js("return arguments[0].getRootNode().host || arguments[0].parentElement",
                           self.open_dialog())
