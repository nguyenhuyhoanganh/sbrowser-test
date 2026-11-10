"""Samsung downloads page (internet://downloads; opened as chrome://downloads).

How it differs from Chromium:
- left side bar: search + category filter (All, Image, Video, Audio, Document, Others)
- a finished row: name, size, source link and icon buttons "Copy link", "Show in folder"
  (aria-label; title "Open Downloads folder") and X "Remove <name> from download history"
- a row in progress: progress text ("704 KB/10.49 MB") and text buttons Pause / Resume
  (#pauseOrResume) and Cancel (#cancelButton); Cancel removes the row (snack bar + Undo)
- toolbar: "Clear download history"
- a finished download also opens the toolbar Downloads bubble
"""
from __future__ import annotations



from sbtest.pages.base import BasePage
from sbtest.web import Element


_JS_ITEM_INFO = r"""
const r = arguments[0].shadowRoot;
const t = s => { const e = r.querySelector(s); return e ? (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim() : ''; };
const visible = e => e && getComputedStyle(e).display !== 'none' && e.getClientRects().length > 0;
const name = r.querySelector('#name');
const progress = r.querySelector('si-progress, #progress, progress, [role=progressbar]');
return {
  name: name ? (name.getAttribute('title') || name.textContent || '').trim() : '',
  url: (r.querySelector('#downloadItemUrl') || {}).href || '',
  size: t('#size'),
  description: t('#inProgressStatus') || t('#description') || t('.description') || t('#progress-size-text'),
  tag: t('#tag'),
  in_progress: visible(progress),
};
"""


class DownloadsPage(BasePage):
    # -- selectors -----------------------------------------------------------------
    page = "downloads"
    ROOT = "downloads-manager >>> #mainContainer"
    TOOLBAR = "downloads-manager >>> #toolbar"
    ITEMS = "downloads-manager >>> downloads-item"
    CLEAR_ALL = "downloads-manager >>> #toolbar >>> #clearAll"
    ROW_BUTTONS = "si-flat-button, si-icon-button, cr-icon-button, button, [role=button]"
    CATEGORIES = ("All", "Image", "Video", "Audio", "Document", "Others")

    # -- read ----------------------------------------------------------------------
    def items(self) -> list[Element]:
        return self.web.find_all(self.ITEMS)

    def info(self, item) -> dict:
        """``{name, url, size, description, tag, in_progress}`` of one row."""
        return self.web.js(_JS_ITEM_INFO, item)

    def names(self) -> list[str]:
        return [self.info(i)["name"] for i in self.items()]

    def item(self, name: str, timeout: float | None = None) -> Element:
        """The row of file ``name``. The list reuses its row elements when it re-renders (a
        download added, removed, restored): a row counts once it shows ``name`` on two
        consecutive polls of the wait, so an action never uses a row that just changed."""
        seen = {}

        def _f():
            for i in self.items():
                if self.info(i)["name"] == name:
                    if seen.get("row") is not None and self.web.same_element(seen["row"], i):
                        return i
                    seen["row"] = i
                    return None   # the next poll reads it again
            seen.clear()
            return None
        return self.web.wait_until(_f, timeout, f"download item {name!r}")

    def row_info(self, name: str) -> dict:
        """``info`` of the row of ``name`` (read again until the row still shows ``name``)."""
        def _f():
            i = self.info(self.item(name, timeout=2))
            return i if i["name"] == name else None
        return self.web.wait_until(_f, message=f"download row {name!r}")

    def status(self, name: str) -> str:
        """Tag, progress / description and size of a row in one string ("Paused 1 MB/10 MB ...")."""
        i = self.row_info(name)
        return " ".join(x for x in (i["tag"], i["description"], i["size"]) if x)

    def row_buttons(self, name: str) -> list[str]:
        """Labels of the buttons a row shows now (Pause / Cancel while in progress, Copy link /
        Show in folder / remove when finished)."""
        buttons = self.web.find_all(f"deepcss={self.ROW_BUTTONS}", within=self.item(name))
        labels = (self.web.text(b) or self.web.attr(b, "aria-label") or self.web.attr(b, "title") for b in buttons)
        return list(dict.fromkeys(x for x in labels if x))

    # -- wait ----------------------------------------------------------------------
    def wait_item(self, name: str, present: bool = True, timeout: float | None = None) -> None:
        self.web.wait_until(lambda: (name in self.names()) == present, timeout,
                            f"download {name!r} {'present' if present else 'absent'}")

    def wait_complete(self, name: str, timeout: float | None = None) -> dict:
        """Wait until the row is finished; returns its ``info``."""
        def _done():
            i = self.row_info(name)
            return i if not i["in_progress"] else None
        return self.web.wait_until(_done, self.web.long_timeout if timeout is None else timeout,
                                   f"download {name!r} complete")

    def wait_status(self, name: str, contains: str, timeout: float | None = None) -> str:
        """Wait until ``status(name)`` contains ``contains`` (e.g. "Paused"); returns it."""
        def _s():
            s = self.status(name)
            return s if contains.lower() in s.lower() else None
        return self.web.wait_until(_s, timeout, f"download {name!r} status containing {contains!r}")

    # -- row buttons ----------------------------------------------------------------
    def action(self, name: str, action: str) -> None:
        """Click a row button by its text, aria-label or title (the named methods below use it)."""
        item = self.item(name)
        for b in self.web.find_all("deepcss=si-flat-button", within=item):   # Pause / Resume / Cancel
            if self.web.text(b) == action:
                self.web.click(b)
                return
        for attr in ("aria-label", "title"):                                  # icon buttons
            hits = self.web.find_all(f'deepcss=[{attr}="{action}"]', within=item)
            if hits:
                self.web.click(hits[0])
                return
        raise LookupError(f"no button {action!r} on download row {name!r}: {self.row_buttons(name)}")

    def pause(self, name: str) -> None:
        """Pause a download in progress."""
        self.action(name, "Pause")
        self.wait_status(name, "Paused")

    def resume(self, name: str) -> None:
        """Resume a paused download."""
        self.action(name, "Resume")
        self.web.wait_until(lambda: "paused" not in self.status(name).lower(), message=f"{name!r} resumed")

    def cancel(self, name: str) -> str:
        """Cancel a download in progress: the row goes away; returns the snack bar text."""
        self.action(name, "Cancel")
        self.wait_item(name, present=False)
        return self.wait_toast()

    def copy_link(self, name: str) -> None:
        """Copy link icon: the download's address goes to the clipboard."""
        self.action(name, "Copy link")

    def show_in_folder(self, name: str) -> None:
        """Show in folder icon: File Explorer opens the folder (check with ``native.wait_explorer``)."""
        self.action(name, "Show in folder")

    def remove(self, name: str) -> None:
        """X of the row: removed from the list (the file stays on disk), snack bar + Undo."""
        self.web.click(self.web.find("deep=#remove", within=self.item(name)))
        self.wait_item(name, present=False)

    # -- toolbar and side bar -------------------------------------------------------
    def clear_all(self) -> None:
        """Toolbar "Clear download history" (cases call it "Clear all"): the list is empty."""
        self.toolbar("Clear download history")
        self.confirm_dialog_if_open("Clear", "Delete", "OK")
        self.web.wait_until(lambda: not self.items(), message="downloads list empty")

    def filter_category(self, label: str) -> None:
        """Side bar category: one of ``CATEGORIES``."""
        self.side_bar(label)
