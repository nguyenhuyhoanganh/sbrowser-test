"""Samsung add-ons page (internet://extensions; opened as chrome://extensions, title "Add-ons").

STATUS: verified on Samsung Browser 31.0.1.40 (Chromium 151) with the Selenium web layer;
ported to Playwright since and not run on a Samsung build yet - run the feature before trusting it.

How it differs from Chromium:
- "Developer mode" is a si-toggle in the LEFT side bar (#devModeToggle); turning it on shows
  "Load Unpacked", "Pack add-on" and "Update" in the toolbar
- cards (extensions-item#<id>): name, version, description, "Details" / "Remove"
  (si-flat-button), dev "Reload" icon (#dev-reload-button) and the on/off si-toggle (#enableToggle)
- side bar: Add-ons, Keyboard shortcuts; list footer: "Get add-ons" (Galaxy Store / web store)
``info()`` (chrome.developerPrivate) works unchanged.
"""
from __future__ import annotations

from playwright.async_api import Error as PlaywrightError

from sbtest.pages.base import BasePage
from sbtest.web import Element

_JS_CARD_NAMES = r"""
return arguments[0].map(c => {
  const n = c.shadowRoot && c.shadowRoot.querySelector('#name');
  return n ? (n.innerText || n.textContent || '').replace(/\s+/g, ' ').trim() : '';
}).filter(Boolean);
"""


class ExtensionsPage(BasePage):
    # -- selectors -----------------------------------------------------------------
    page = "extensions"
    ROOT = "extensions-manager >>> #items-list"
    TOOLBAR = "extensions-manager >>> #toolbar"
    ITEMS = "extensions-manager >>> #items-list >>> extensions-item"
    DEV_MODE = "extensions-manager >>> #sidebar >>> #devModeToggle"
    LOAD_UNPACKED = "extensions-manager >>> #toolbar >>> #loadUnpacked"
    SHORTCUTS = "extensions-manager >>> #sidebar >>> #shortcutButton"
    GET_ADDONS = "extensions-manager >>> #items-list >>> #webstore-button"

    # -- read ----------------------------------------------------------------------
    def info(self) -> list[dict]:
        """``[{id, name, version, state, type, location}]`` straight from the extension system."""
        return self.web.js(
            "return new Promise(done => chrome.developerPrivate.getExtensionsInfo("
            "{includeDisabled: true, includeTerminated: true},"
            " l => done(l.map(e => ({id: e.id, name: e.name, version: e.version, state: e.state,"
            " type: e.type, location: e.location})))));")

    def names(self) -> list[str]:
        """Names shown as cards in the UI (one read: the list re-renders while it filters)."""
        for attempt in range(5):
            try:
                return self.web.js(_JS_CARD_NAMES, self.web.find_all(self.ITEMS))
            except PlaywrightError:
                if attempt == 4:
                    raise
        return []

    def item(self, name: str, timeout: float | None = None) -> Element:
        """The card of add-on ``name``."""
        def _f():
            for i in self.web.find_all(self.ITEMS):
                if self.web.text(self.web.find("deep=#name", within=i, timeout=1)) == name:
                    return i
            return None
        return self.web.wait_until(_f, timeout, f"extension card {name!r}")

    def ext_id(self, name: str) -> str:
        return self.web.attr(self.item(name), "id")

    def is_enabled(self, name: str) -> bool:
        """State of the card's on/off toggle."""
        return self.web.is_checked(self.web.find("deep=#enableToggle", within=self.item(name)))

    def dev_mode(self) -> bool:
        return self.web.is_checked(self.DEV_MODE)

    def dev_toolbar(self) -> list[str]:
        """Labels of the toolbar buttons shown (developer mode adds Load Unpacked / Pack / Update)."""
        return self.toolbar_labels()

    def shortcuts(self) -> dict[str, str]:
        """Keyboard shortcuts page: ``{"Activate add-on for <name>": "Not set" | "Ctrl+..."}``."""
        out = {}
        for el in self.web.find_all('deepcss=[aria-label^="Shortcut "]'):
            # an empty shortcut shows "Not set" as the input placeholder
            out[self.web.attr(el, "aria-label")[len("Shortcut "):]] = (
                self.web.value(el) or self.web.text(el) or self.web.attr(el, "placeholder") or "")
        return out

    # -- wait ----------------------------------------------------------------------
    def wait_installed(self, name: str, timeout: float | None = None) -> dict:
        """Wait until the extension system reports ``name`` (any state); returns its info."""
        return self.web.wait_until(lambda: next((e for e in self.info() if e["name"] == name), None),
                                   timeout or self.web.long_timeout, f"{name!r} installed")

    def wait_gone(self, name: str, timeout: float | None = None) -> None:
        self.web.wait_until(lambda: name not in [e["name"] for e in self.info()], timeout, f"{name!r} removed")

    # -- card ----------------------------------------------------------------------
    def set_enabled(self, name: str, on: bool = True) -> None:
        """Turn the add-on on or off with its card toggle."""
        self.web.set_checked(self.web.find("deep=#enableToggle", within=self.item(name)), on)

    def open_details(self, name: str) -> None:
        """Card Details: the details view (URL ``?id=...``)."""
        self.web.click(self._card_button(name, "Details"))
        self.web.wait_url("?id=")

    def reload(self, name: str) -> None:
        """Developer mode -> the card's Reload icon (an unpacked add-on reads its files again)."""
        self.set_dev_mode(True)
        self.web.click(self.web.find("deep=#dev-reload-button", within=self.item(name)))

    def click_remove(self, name: str) -> None:
        """Card Remove; answer the confirmation that follows with ``confirm_remove``."""
        self.web.click(self._card_button(name, "Remove"))

    def confirm_remove(self, native=None, confirm: bool = True) -> None:
        """Answer the remove confirmation - a si-dialog on the page, or a native prompt."""
        if self.has_dialog() or self._wait_dialog(2):
            self.dialog_button("Remove" if confirm else "Cancel")
            self.wait_dialog_closed()
            return
        if native is None:
            raise RuntimeError("no remove confirmation on the page; pass `native` for the browser prompt")
        dlg = native.wait_dialog("remove_extension")
        dlg.click("Remove" if confirm else "Cancel")
        dlg.wait_closed()   # a click on the card while it fades out is lost

    def remove(self, name: str, native, confirm: bool = True) -> None:
        """Card Remove -> 'Delete <name>?' -> Remove (or Cancel); waits until it is gone (or stays)."""
        self.click_remove(name)
        self.confirm_remove(native, confirm)
        if confirm:
            self.wait_gone(name)
        else:
            self.item(name)

    def _card_button(self, name: str, label: str):
        return self.find_by_text("si-flat-button", label, within=self.item(name))

    def _wait_dialog(self, timeout: float) -> bool:
        try:
            self.open_dialog(timeout=timeout)
            return True
        except TimeoutError:
            return False

    # -- developer mode and toolbar --------------------------------------------------
    def set_dev_mode(self, on: bool = True) -> None:
        """Developer mode toggle in the side bar."""
        self.web.set_checked(self.DEV_MODE, on)

    def load_unpacked(self, native, folder) -> None:
        """Developer mode -> toolbar "Load Unpacked" -> Windows folder picker -> folder."""
        self.set_dev_mode(True)
        self.toolbar("Load Unpacked")
        native.file_dialog("open").select_folder(folder)

    def update(self) -> None:
        """Developer mode -> toolbar "Update": every add-on is updated / reloaded now."""
        self.set_dev_mode(True)
        self.toolbar("Update")

    def open_pack_dialog(self) -> None:
        """Developer mode -> toolbar "Pack add-on" -> Pack extension dialog (si-dialog)."""
        self.set_dev_mode(True)
        self.toolbar("Pack add-on")
        self.open_dialog()

    def pack_inputs(self):
        """(root directory input, private key input) of the open Pack extension dialog."""
        inputs = self.web.find_all("deepcss=input", within=self._dialog_host())
        return inputs[0], inputs[1]

    def pack_button_enabled(self) -> bool:
        btn = self.find_by_text(self.DIALOG_BUTTON, "Pack extension", within=self._dialog_host())
        return not self.web.js("return arguments[0].hasAttribute('disabled') || "
                               "(arguments[0].shadowRoot && !!arguments[0].shadowRoot.querySelector('button[disabled]'))", btn)

    def pack(self, folder) -> None:
        """Pack an unpacked add-on folder: writes <folder>.crx and <folder>.pem next to it."""
        self.open_pack_dialog()
        self.web.type(self.pack_inputs()[0], str(folder))
        self.web.wait_until(self.pack_button_enabled, message="Pack extension enabled")
        self.dialog_button("Pack extension")

    # -- side bar and footer -------------------------------------------------------------
    def open_shortcuts(self) -> None:
        """Side bar Keyboard shortcuts (URL ``/shortcuts``); read them with ``shortcuts()``."""
        self.web.click(self.SHORTCUTS)
        self.web.wait_url("/shortcuts")

    def get_addons(self) -> None:
        """"Get add-ons" under the list: opens the add-on store in a new tab (switched to)."""
        before = self.web.tabs
        self.web.click(self.GET_ADDONS)
        self.web.wait_new_tab(before)
