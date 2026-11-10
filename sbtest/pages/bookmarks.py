"""Samsung bookmark manager (internet://bookmarks; opened as chrome://bookmarks).

STATUS: verified on Samsung Browser 31.0.1.40 (Chromium 151) with the Selenium web layer;
ported to Playwright since and not run on a Samsung build yet - run the feature before trusting it.

How it differs from Chromium:
- rows are selected with a round check box (si-select); Edit / Share / Delete / Select all
  live in the page toolbar and act on the selection (no ⋮ per row)
- right click on a row opens a menu: Edit, Delete, Open all (n) in new tab / window / Secret mode
- right ⋮ (toolbar): Add bookmark (same dialog as Edit), Sort by name, Open all (n) in new
  tabs / new window / Secret mode (n = the selected rows)
- "Create folder" adds "Folder 1" in the selected folder, opens it and puts its name in edit
  mode in the left tree (type the name + Enter)
- Delete removes at once and shows a snack bar "1 bookmark deleted" with Undo
- left ⋮ (Options): Create folder in selected folder, Sort by name, Import bookmarks (opens
  Settings in a new tab), Export bookmarks (Windows Save As, HTML)
- Sort by name puts folders first, then bookmarks A-Z
- root folders: "PC bookmarks" > "Bookmark bar"
"""
from __future__ import annotations


from sbtest.pages.base import BasePage, q
from sbtest.web import Element, Keys


class BookmarksPage(BasePage):
    # -- selectors -----------------------------------------------------------------
    page = "bookmarks"
    ROOT = "bookmarks-app >>> bookmarks-list"
    TOOLBAR = "bookmarks-app >>> bookmarks-toolbar"
    ITEMS = "bookmarks-app >>> bookmarks-list >>> bookmarks-item"
    ITEM_TITLE = "bookmarks-app >>> bookmarks-list >>> bookmarks-item >>> #website-title"
    TREE_ITEM = "deepcss=#container[role=treeitem]"
    EDIT_DIALOG = "bookmarks-app >>> bookmarks-command-manager >>> bookmarks-edit-dialog"
    RIGHT_MENU = "bookmarks-app >>> bookmarks-toolbar >>> #menuButton"        # right ⋮ of the list
    OPTIONS_MENU = "bookmarks-app >>> bookmarks-toolbar >>> si-toolbar.bookmarks-toolbar >>> #moreMenuButton"  # left ⋮
    UNDO = "bookmarks-app >>> #undoButton"
    BAR_FOLDER = "Bookmark bar"
    ROOT_FOLDERS = ("PC bookmarks", "Bookmark bar")

    # -- read ----------------------------------------------------------------------
    def titles(self) -> list[str]:
        """Titles shown in the list for the current folder / search, in order."""
        return [self.web.attr(el, "title") or self.web.text(el) for el in self.web.find_all(self.ITEM_TITLE)]

    def item(self, title: str, timeout: float | None = None) -> Element:
        """The row of ``title`` in the list."""
        return self.web.find(f"bookmarks-app >>> bookmarks-list >>> bookmarks-item[aria-label={q(title)}]", timeout)

    def has_item(self, title: str) -> bool:
        return title in self.titles()

    def item_url(self, title: str) -> str:
        """Address shown under a bookmark's title."""
        return self.web.text(self.web.find("deep=si-searched-label.url", within=self.item(title)))

    def is_folder(self, title: str) -> bool:
        """True when the row is a folder."""
        return bool(self.web.find_all("deep=#folderIcon", within=self.item(title)))

    def is_selected(self, title: str) -> bool:
        """True when the row's check box is ticked."""
        return self.web.is_checked(self.web.find("deep=#checkbox", within=self.item(title)))

    def folders(self) -> list[str]:
        """Folder names of the left tree (root folders included)."""
        return [self.web.attr(e, "aria-label") for e in self.web.find_all(self.TREE_ITEM)]

    def selected_folder(self) -> str:
        """The folder open in the list (selected in the left tree)."""
        sel = [self.web.attr(e, "aria-label") for e in self.web.find_all(self.TREE_ITEM)
               if "selected" in (self.web.attr(e, "class") or "")]
        return sel[0] if sel else ""

    # -- wait ----------------------------------------------------------------------
    def wait_titles(self, expected: list[str], timeout: float | None = None) -> list[str]:
        return self.web.wait_until(lambda: self.titles() if self.titles() == expected else None,
                                   timeout, f"bookmark titles == {expected}")

    def wait_item(self, title: str, present: bool = True, timeout: float | None = None) -> None:
        self.web.wait_until(lambda: self.has_item(title) == present, timeout,
                            f"bookmark {title!r} {'present' if present else 'absent'}")

    # -- navigate ------------------------------------------------------------------
    def open_folder(self, name: str) -> None:
        """Click a folder in the left tree; the list shows its content."""
        self.web.click(f"deepcss=#container[role=treeitem][aria-label={q(name)}]")
        self.web.wait_until(lambda: self.selected_folder() == name, message=f"folder {name} selected")

    def open_item(self, title: str) -> None:
        """Click the row: opens a folder in the list, or the bookmarked page in a NEW TAB
        (switched to)."""
        before = self.web.tabs
        is_folder = self.is_folder(title)
        self.web.click(self.web.find("deep=#website-title", within=self.item(title)))
        if not is_folder:
            self.web.wait_new_tab(before)

    # -- menus ---------------------------------------------------------------------
    def options(self, action: str) -> str:
        """Right ⋮ of the list: ``Add bookmark`` | ``Sort by name`` | ``Open all (n) in new
        tabs`` / ``... new window`` / ``... Secret mode`` (prefix match). Returns the label."""
        self.web.click(self.RIGHT_MENU)
        return self.choose_menu_item(action, "options menu")

    def organize(self, action: str) -> str:
        """Left ⋮: ``Create folder in selected folder`` | ``Sort by name`` |
        ``Import bookmarks`` | ``Export bookmarks``. Returns the label."""
        self.web.click(self.OPTIONS_MENU)
        return self.choose_menu_item(action, "organize menu")

    def item_menu(self, title: str, action: str) -> str:
        """Right click a row: ``Edit`` | ``Delete`` | ``Open all (1) in new tab`` | ``... new window``
        | ``... Secret mode`` (prefix match). Returns the label."""
        self.web.right_click(self.web.find("deep=#website-title", within=self.item(title)))
        return self.choose_menu_item(action, "bookmark context menu")

    # -- add -----------------------------------------------------------------------
    def add_bookmark(self, name: str, url: str) -> None:
        """Right ⋮ > Add bookmark -> Name + Web address -> Save (into the open folder)."""
        self.options("Add bookmark")
        self.open_dialog()
        self._fill_edit_dialog(name, url)
        self.save_dialog()
        self.wait_item(name)

    def add_folder(self, name: str) -> None:
        """Toolbar "Create folder" in the current folder, type the name in the tree, Enter.
        Goes back to the parent folder so the new folder shows in ``titles()``."""
        parent = self.selected_folder()
        before = set(self.folders())
        self.toolbar("Create folder")
        new = self.web.wait_until(lambda: next((f for f in self.folders() if f not in before), None),
                                  message="new folder in tree")
        # the new name field has the focus with "Folder N" in it (readonly to clicks): type over it
        self.web.wait_until(lambda: self.web.js(
            "let a = document.activeElement; while (a && a.shadowRoot && a.shadowRoot.activeElement)"
            " a = a.shadowRoot.activeElement; return a && a.id === 'input' && a.getAttribute('aria-label') === arguments[0]",
            new), message=f"{new!r} name field focused")
        self.web.press(Keys.CONTROL, "a")
        self.web.type_keys(name, enter=True)
        self.web.wait_until(lambda: name in self.folders(), message=f"folder {name!r} in tree")
        if parent:
            self.open_folder(parent)
        self.wait_item(name)

    # -- edit ----------------------------------------------------------------------
    def edit(self, title: str, name: str | None = None, url: str | None = None) -> None:
        """Select the row -> toolbar Edit -> change name / URL -> Save."""
        self.select(title)
        self.toolbar("Edit")
        self.open_dialog()
        self._fill_edit_dialog(name, url)
        self.save_dialog()
        if name is not None:
            self.wait_item(name)

    def rename(self, title: str, new_name: str) -> None:
        """Change a bookmark's or folder's name (toolbar Edit)."""
        self.edit(title, name=new_name)

    def save_dialog(self) -> None:
        """Save of the open Add / Edit dialog (enabled once a field changed)."""
        save = f"{self.EDIT_DIALOG} >>> #saveButton >>> #siDialogButton"
        self.web.wait_until(lambda: self.web.is_enabled(save), message="Save enabled (a field changed)")
        self.web.click(save)
        self.wait_dialog_closed()

    def _fill_edit_dialog(self, name: str | None, url: str | None) -> None:
        if name is not None:
            self.web.type(f"{self.EDIT_DIALOG} >>> #name >>> #input", name)
        if url is not None:
            self.web.type(f"{self.EDIT_DIALOG} >>> #url >>> #input", url)

    def sort_by_name(self) -> None:
        """Right ⋮ > Sort by name: folders first, then bookmarks A-Z."""
        self.options("Sort by name")

    # -- delete ----------------------------------------------------------------------
    def delete(self, title: str) -> str:
        """Select + toolbar Delete; returns the snack bar text ("1 bookmark deleted")."""
        self.select(title)
        toast = self.delete_selected()
        self.wait_item(title, present=False)
        return toast

    def delete_selected(self) -> str:
        """Toolbar Delete ("Delete all" when every row is selected); returns the snack bar text."""
        self.toolbar_any("Delete", "Delete all")
        return self.wait_toast("deleted")

    def undo(self) -> None:
        """Undo of the snack bar after a delete."""
        self.web.click(self.UNDO)

    # -- selection -------------------------------------------------------------------
    def select(self, *titles: str) -> None:
        """Tick the round check box of each row (multi-select needs no Ctrl)."""
        for t in titles:
            if not self.is_selected(t):
                self.web.click(self.web.find("deep=#checkbox", within=self.item(t)))
        self.web.wait_until(lambda: all(self.is_selected(t) for t in titles), message=f"{titles} selected")

    def select_all(self) -> None:
        """Toolbar Select all: every row of the open folder."""
        self.toolbar("Select all")
        self.web.wait_until(lambda: all(self.is_selected(t) for t in self.titles()), message="all rows selected")

    def deselect_all(self) -> None:
        """Toolbar Deselect all (shown while every row is selected)."""
        self.toolbar("Deselect all")
        self.web.wait_until(lambda: not any(self.is_selected(t) for t in self.titles()), message="no row selected")

    # -- open in tabs / files ---------------------------------------------------------
    def open_all(self, *titles: str, where: str = "new tab") -> str:
        """Select ``titles`` (none: Select all) -> right ⋮ > "Open all (n) in new tabs" |
        "... new window" | "... Secret mode" (``where`` = ``new tab`` | ``new window`` |
        ``Secret mode``). n counts the SELECTED rows. Returns the label clicked."""
        self.select(*titles) if titles else self.select_all()
        self.web.click(self.RIGHT_MENU)
        items = self.web.wait_until(lambda: self.menu_items() or None, message="options menu")
        match = next((i for i in items if i.startswith("Open all") and where in i), None)
        if match is None:
            raise LookupError(f"no 'Open all ... {where}' in options menu {items}")
        self.click_menu_item(match)
        return match

    def export(self, native, path) -> None:
        """Left ⋮ > Export bookmarks -> Windows Save As (HTML file)."""
        self.organize("Export bookmarks")
        native.file_dialog("save").save_as(path)

    def open_import(self) -> None:
        """Left ⋮ > Import bookmarks: opens Settings (import) in a new tab, switched to."""
        before = self.web.tabs
        self.organize("Import bookmarks")
        self.web.wait_new_tab(before)
