"""Samsung history page (internet://history; opened as chrome://history).

How it differs from Chromium:
- one history-item per entry; the first entry of a day also carries the day header
  ("Today - Tuesday, October 20, 2026") with its own select-all check box (#all-select)
- entries are selected with a round check box (si-select#select); Share / Delete act on
  the selection, "Clear history" is always in the toolbar; Delete and Clear history act at
  once, with no confirmation
- no ⋮ per row: right click a row -> Open all (1) in new tab / new window / Secret mode,
  More results from same site, Copy link, Delete, Inspect
- left side bar: search, time filter (All time / Last hour / Today / Yesterday / Older),
  "Clear browsing data" (opens internet://settings/clearBrowserData in a new tab)
"""
from __future__ import annotations

from sbtest.pages.base import BasePage
from sbtest.web import Element


_JS_ROWS = r"""
return arguments[0].map(i => {
  const r = i.shadowRoot, link = r.querySelector('#item-container');
  const txt = s => { const e = r.querySelector(s); return e ? e.textContent.replace(/\s+/g, ' ').trim() : ''; };
  const t = r.querySelector('#history-item-title');
  // every row holds a day header; only the first row of a day (is-card-start) shows it
  const day = i.hasAttribute('is-card-start') ? txt('#date-accessed .card-header > span') : '';
  return {title: t ? t.title : '', url: link ? link.href : '', domain: txt('.website-domain'),
          time: txt('#time-accessed'), day: day};
});
"""


class HistoryPage(BasePage):
    # -- selectors -----------------------------------------------------------------
    page = "history"
    ROOT = "#history-app >>> #history"
    TOOLBAR = "#history-app >>> #toolbar"
    ITEMS = "#history-app >>> #history >>> history-item"
    CLEAR_DATA_LINK = "#history-app >>> #content-side-bar >>> #clear-browsing-data"
    TIME_FILTERS = ("All time", "Last hour", "Today", "Yesterday", "Older")

    # -- read ----------------------------------------------------------------------
    def items(self) -> list[Element]:
        return self.web.find_all(self.ITEMS)

    def rows(self) -> list[dict]:
        """``[{title, url, domain, time, day}]`` of the listed entries (newest first); ``day``
        is set on the first entry of each day only."""
        return self.web.js(_JS_ROWS, self.items())

    def titles(self) -> list[str]:
        return [r["title"] for r in self.rows()]

    def urls(self) -> list[str]:
        return [r["url"] for r in self.rows()]

    def days(self) -> list[str]:
        """Day headers in order ("Today - Tuesday, October 20, 2026", ...)."""
        return [r["day"] for r in self.rows() if r["day"]]

    def item(self, title: str, timeout: float | None = None) -> Element:
        """The row of ``title`` (the newest when it was visited several times)."""
        def _f():
            for i in self.items():
                if self.web.js("const t = arguments[0].shadowRoot.querySelector('#history-item-title');"
                               "return t ? t.title : ''", i) == title:
                    return i
            return None
        return self.web.wait_until(_f, timeout, f"history item {title!r}")

    def has_item(self, title: str) -> bool:
        return title in self.titles()

    def is_empty(self) -> bool:
        return not self.items()

    def is_selected(self, title: str) -> bool:
        return self.web.is_checked(self.web.find("deep=si-select#select", within=self.item(title)))

    def time_filters(self) -> list[str]:
        """Ticked time filters. They are check boxes: several can be on (union of ranges)."""
        out = []
        for el in self.web.find_all("deepcss=si-select.si-nav-menu-item"):
            label = self.web.js("return (arguments[0].textContent || '').replace(/\\s+/g, ' ').trim()", el)
            if label in self.TIME_FILTERS and self.web.is_checked(el):
                out.append(label)
        return out

    # -- wait ----------------------------------------------------------------------
    def wait_item(self, title: str, present: bool = True, timeout: float | None = None) -> None:
        self.web.wait_until(lambda: self.has_item(title) == present, timeout,
                            f"history item {title!r} {'present' if present else 'absent'}")

    def wait_titles(self, expected: list[str], timeout: float | None = None) -> list[str]:
        """Wait until the list shows exactly ``expected`` (search and filters are debounced)."""
        return self.web.wait_until(lambda: self.titles() if self.titles() == expected else None,
                                   timeout, f"history titles == {expected}")

    # -- open ----------------------------------------------------------------------
    def open_item(self, title: str) -> None:
        """Click the entry: the page opens in the same tab."""
        self.web.click(self.web.find("deep=#history-item-title", within=self.item(title)))

    def item_menu(self, title: str, action: str) -> str:
        """Right click a row: ``Open all (1) in new tab`` / ``... new window`` / ``... Secret mode`` |
        ``More results from same site`` | ``Copy link`` | ``Delete`` (prefix match). Returns the label."""
        self.web.right_click(self.web.find("deep=#history-item-title", within=self.item(title)))
        return self.choose_menu_item(action, "history context menu")

    def more_from_site(self, title: str) -> None:
        """Right click > More results from same site: the list shows only that site's entries."""
        self.item_menu(title, "More results from same site")

    def open_clear_browsing_data(self) -> None:
        """Side bar "Clear browsing data": Settings > Clear browsing data in a new tab, switched to."""
        before = self.web.tabs
        self.web.click(self.CLEAR_DATA_LINK)
        self.web.wait_new_tab(before)

    # -- select --------------------------------------------------------------------
    def select(self, *titles: str) -> None:
        """Tick the round check box of each entry."""
        for t in titles:
            if not self.is_selected(t):
                self.web.click(self.web.find("deep=si-select#select", within=self.item(t)))
        self.web.wait_until(lambda: all(self.is_selected(t) for t in titles), message=f"{titles} selected")

    def select_day(self, day: int = 0) -> None:
        """Tick the day header's check box (``day`` = 0 for the newest day): every entry of that day."""
        firsts = [i for i in self.items() if self.web.attr(i, "is-card-start") is not None]
        if day >= len(firsts):
            raise LookupError(f"no day {day}: the list shows {len(firsts)} day(s)")
        self.web.click(self.web.find("deep=#all-select", within=firsts[day]))

    # -- delete --------------------------------------------------------------------
    def delete_selected(self, confirm: bool = True) -> None:
        """Toolbar Delete: removes the selected entries (answers a confirmation if one shows)."""
        self.toolbar("Delete")
        self.answer_dialog_if_open(confirm, ("Delete", "Remove", "OK"))

    def remove(self, title: str) -> None:
        """Tick one entry + toolbar Delete; waits until it is gone."""
        self.select(title)
        self.delete_selected()
        self.wait_item(title, present=False)

    def delete_from_menu(self, title: str) -> None:
        """Right click > Delete on one entry; waits until it is gone."""
        self.item_menu(title, "Delete")
        self.answer_dialog_if_open(True, ("Delete", "Remove", "OK"))
        self.wait_item(title, present=False)

    def delete_day(self, day: int = 0) -> None:
        """Day header check box + toolbar Delete: every entry of that day."""
        self.select_day(day)
        self.delete_selected()

    def clear_history(self, confirm: bool = True) -> None:
        """Toolbar "Clear history". Samsung clears at once with no confirmation; when a build
        asks, ``confirm`` answers it (False = Cancel)."""
        self.toolbar("Clear history")
        self.answer_dialog_if_open(confirm, ("Clear", "Delete", "Clear history", "OK"))

    # -- filter --------------------------------------------------------------------
    def filter_time(self, *labels: str) -> None:
        """Leave exactly ``labels`` ticked among ``TIME_FILTERS`` (ticks first, then unticks)."""
        for label in labels:
            if label not in self.time_filters():
                self.side_bar(label)
        for label in self.time_filters():
            if label not in labels:
                self.side_bar(label)
        self.web.wait_until(lambda: sorted(self.time_filters()) == sorted(labels), message=f"time filters {labels}")
