# Action catalogue: a case step -> the call

Names in quotes (`"bookmarks_button"`) are keys of `config/native_ui.yaml`; `name=` fills
their `{name}` placeholder. The reason behind a call (focus, toasts, bubbles) is in
`references/feature-notes.md`. Preconditions: `references/writing-tests.md`. No row fits ->
add a page-object method or a ui-map entry, then a row here.

## Contents

- Pages and navigation
- Bookmarks manager (`pages.bookmarks`)
- Bookmarks in the browser UI
- History (`pages.history`)
- Downloads (`pages.downloads`)
- Add-ons (`pages.extensions`)
- Dialogs, bubbles, files
- Reading and asserting

## Pages and navigation

| the case says | do |
|---|---|
| open a web page | `web.open(site.page("Title"))`, `web.open(site.url("/form.html"))` |
| open Bookmarks / History / Downloads / Add-ons | `pages.bookmarks.open()` / `pages.history.open()` / `pages.downloads.open()` / `pages.extensions.open()` |
| type an address in the address bar | `native.navigate("internet://history")` |
| read the address bar | `native.omnibox_text()`; compare with `cfg.display_url("history")` |
| back / forward / reload / home button | `native.click("back_button")` / `"forward_button"` / `"reload_button"` / `"home_button"` |
| back / forward inside the test, no button | `web.back()` / `web.forward()` |
| a browser shortcut (Ctrl+D/H/J/T/W/L, F5) | `native.hotkey("^d")` |
| Enter / Esc / Ctrl+A inside a page | `web.press("ENTER")`, `web.press(Keys.CONTROL, "a")` |
| something opens in a tab | `web.switch_tab(url=cfg.page_url("history"))` or `web.switch_tab(title="X")` |
| a new tab opens | `before = web.tabs` before the action, then `web.wait_new_tab(before)` |
| a tab opens in the background (add-on options) | `"X" in native.tab_titles()`, `native.click({"control_type": "TabItem", "title": "X"})`, read it with `native.wait_text("(?i)...")` |
| app menu > item | `native.menu("Add-ons")`, `native.menu("History", "History")` |
| iframe content | `with web.frame("#inner"): ...` |
| a navigation that stops at an HTTP sign-in prompt | `web.open(url, blocking=False)`, then `native.wait_dialog("http_auth")` |
| restart the browser, check it persisted | `session.restart(); bm = pages.of(session.web).bookmarks.open()` |

## Bookmarks manager (`pages.bookmarks`)

| the case says | do |
|---|---|
| list / check an entry | `bm.titles()`, `bm.wait_item("X")`, `bm.wait_item("X", present=False)`, `bm.is_folder("X")`; address: `bm.item_url("X") == site.url("/pages/page1.html")` (the full URL) |
| open a folder | `bm.open_folder("Work")`; the bar: `bm.open_folder(bm.BAR_FOLDER)`; the tree: `bm.folders()` |
| add a bookmark | `bm.add_bookmark(name, url)` (into the open folder) |
| add a folder | `bm.add_folder(name)` |
| edit name / address | `bm.edit("X", name=..., url=...)`, `bm.rename("X", "Y")` |
| a row's right-click menu | `bm.item_menu("X", "Edit")` / `"Delete"` / `"Open all (2) in new tab"`; after Delete: `bm.wait_toast("deleted")` |
| delete (toolbar) and undo | `toast = bm.delete("X")`, `bm.undo()` |
| select several / all | `bm.select("A", "B")`, `bm.is_selected("A")`, `bm.select_all()`, `bm.deselect_all()`, `bm.delete_selected()` |
| sort / menus | `bm.sort_by_name()`, `bm.options("...")` (right ⋮), `bm.organize("...")` (left ⋮) |
| open all bookmarks of a folder | `bm.open_all()`, `bm.open_all("A", "B", where="new window")` / `where="Secret mode"` |
| import bookmarks | `bm.open_import()` (Settings import page in a new tab, switched to) |
| open a bookmark | `bm.open_item("X")` (new tab, switched to) |
| search | `bm.search("ta")`, `bm.wait_titles([...])` |
| export to a file | `bm.export(native, tmp_path / "b.html")` |

## Bookmarks in the browser UI

| the case says | do |
|---|---|
| Ctrl+D -> "Page bookmarked." | `native.focus_page(); native.hotkey("^d"); toast = native.wait_dialog("bookmark_added")` |
| toast Edit -> rename | at once: `toast.click("Edit")`; `field = native.element("bookmark_edit_name", in_main=False)`, `field.set_focus()`, `native.hotkey("^a", focus=False)`, `native.type_text("New name")`, `native.click("bookmark_edit_save")`; read a field: `native.element("bookmark_edit_url", in_main=False).get_value()` |
| the page is bookmarked (star) | `def star(): native.focus_page(); return native.exists("bookmark_star_filled")`, then `web.wait_until(star)` or `web.wait_until(lambda: not star())` |
| remove with the star | `native.wait_dialog_gone("bookmark_added")`, then `native.click("bookmark_star_filled")` |
| Bookmarks panel (toolbar) | `native.click("bookmarks_button")`; folder `native.click("bookmarks_panel_folder", name="Bookmark bar")`; bookmark `native.click("bookmarks_panel_item", name="X")`; buttons `"bookmarks_panel_add_page"`, `"bookmarks_panel_create_folder"`, `"bookmarks_panel_expand"` (opens the manager) |

## History (`pages.history`)

| the case says | do |
|---|---|
| entries, order, details | `h.titles()`, `h.rows()` -> `{title, url, domain, time, day}`, `h.days()` |
| open an entry | `h.open_item("Alpha")` (same tab) |
| select / delete / cancel | `h.select("A", "B")`, `h.is_selected("A")`, `h.delete_selected()`, `h.remove("A")`, `h.cancel_selection()` |
| a row's right-click menu | `h.item_menu("A", "Copy link")`, `h.delete_from_menu("A")`, `h.more_from_site("A")` |
| delete a day | `h.delete_day(0)` (0 = newest), or `h.select_day(0)` + `h.delete_selected()` |
| clear history | `h.clear_history()` |
| clear browsing data link | `h.open_clear_browsing_data()` (new tab, switched to) |
| time filter | `h.filter_time("Last hour")`, `h.filter_time("Yesterday", "Today")`, `h.time_filters()` |
| search | `h.search("Gam")`, `h.wait_titles(["Gamma"])`; nothing found: `web.wait_until(h.is_empty)` |
| toolbar button state | `h.toolbar_enabled("Delete")` |
| Ctrl+H | `native.hotkey("^h")`, `web.switch_tab(url=cfg.page_url("history"))` |

## Downloads (`pages.downloads`)

| the case says | do |
|---|---|
| row details | `d.wait_complete("x")` -> `{name, url, size, description, tag, in_progress}`, `d.names()` |
| file on disk | `web.wait_file(downloads_dir, "x")` |
| pause / resume / cancel | `d.pause("slow.bin")`, `d.resume("slow.bin")`, `toast = d.cancel("slow.bin")`; `d.status("slow.bin")`, `d.wait_status("slow.bin", "Paused")` |
| the buttons of a row | `d.row_buttons("x")` |
| remove and undo | `d.remove("x")`; snack bar text: `d.wait_toast("removed")`; then `d.toast_action("Undo")`, `d.wait_item("x")` |
| clear the list ("Clear all") | `native.close_download_bubble()` after a fresh download, then `d.clear_all()` |
| category / search | `d.filter_category("Image")`, `d.search("ta.bin")` |
| copy link | `d.copy_link("x")`, then read the clipboard (Reading and asserting) |
| show in folder | `d.show_in_folder("x")`, `win = native.wait_explorer(downloads_dir.name)`, `native.explorer_has_selected(win, "x")`, `win.close()` |
| the toolbar Downloads bubble | `native.element("download_bubble_item", title_re=r"^x ")` (name "x 2,048 B • Done") |
| ask where to save | `browser(prefs={"download.prompt_for_download": True})`, `native.file_dialog("save").save_as(path)` |
| Ctrl+J | `native.hotkey("^j")`, `web.switch_tab(url=cfg.page_url("downloads"))` |

## Add-ons (`pages.extensions`)

| the case says | do |
|---|---|
| card / state | `e = pages.extensions.open()`, `e.names()`, `e.item("X")`, `e.is_enabled("X")`, `e.info()` (id, version, state) |
| turn on / off | `e.set_enabled("X", False)` |
| the add-on works on a page | `web.js("return document.documentElement.getAttribute('data-sb-addon')") == "active"` |
| developer mode | `e.set_dev_mode(True)`, `e.dev_toolbar()`, `e.reload("X")`, `e.update()` |
| details / shortcuts | `e.open_details("X")`, `e.open_shortcuts()`, `e.shortcuts()` |
| remove (or cancel) | `e.remove("X", native)` / `e.remove("X", native, confirm=False)`; the prompt itself: `e.click_remove("X")`, `dlg = native.wait_dialog("remove_extension")`, `dlg.texts()`, `dlg.click("Remove")` |
| install unpacked / from the store | `e.load_unpacked(native, folder)`, `pages.webstore.install(store_id, native)` |
| pack | `e.open_pack_dialog()`, `e.pack_inputs()`, `e.pack_button_enabled()`, `e.pack(folder)` |
| "Get add-ons" link | `e.get_addons()` (new tab, switched to) |
| toolbar Add-ons menu | `native.click("extensions_button")`; `native.click("addons_menu_pin", name="X")`, `"addons_menu_unpin"`, `"addons_menu_more"`, then `native.menu_items()` / `native.select_menu_items("Options")` |
| pinned icon -> popup | `native.click("extension_action", name="X")`; popup content: `native.element({"auto_id": "count"}, in_main=False)` |

## Dialogs, bubbles, files

| the case says | do |
|---|---|
| a browser bubble or prompt | `dlg = native.wait_dialog("<dialogs key>" or "(?i)regex")`, `dlg.texts()`, `dlg.click("Label")`, `dlg.click_any("A", "B")`, `dlg.wait_closed()` |
| a bubble or toast is gone | `native.wait_dialog_gone("bookmark_added")` |
| a dialog inside an internal page | `page.open_dialog()`, `page.dialog_text()`, `page.dialog_input("name")`, `page.dialog_button("Save")` |
| upload through the Windows Open dialog | `web.click("#pick")`, `native.file_dialog("open").open(f1, f2)` |
| upload through `<input type=file>` | `web.upload("#file", path)` |
| Save As | `native.file_dialog("save").save_as(path)` |
| choose a folder | `native.file_dialog("open").select_folder(path)` |
| drag a file from Explorer | `native.drag_file_from_explorer(path, web=web, target="#drop-zone")` |
| JS alert / confirm / prompt | `with web.dialog(accept=True, prompt_text="x") as d:` around the action, then `d.text` |
| "Leave site?" | `with web.dialog(accept=False) as d: web.open(url, blocking=False)`, then `d.type == "beforeunload"` |
| drag and drop in a page | `web.drag_and_drop(a, b, method="html5")` / `"actions"` / `"native"` |
| a Windows notification | `native.wait_os_toast("(?i)text")` |
| print preview | `native.wait_dialog("print")`, `.press("{ESC}")` (no `web.*` while it is open) |
| right-click a link -> menu item | `native.context_menu_web(web, "#next", "Open in new tab")` |

## Reading and asserting

| the case says | do |
|---|---|
| text on a page | `web.text(loc)`, `web.wait_text(loc, "x")`, `web.wait_page_text("x")` |
| snack bar of an internal page | `text = page.wait_toast("deleted")` (waits for a snack bar containing the text, returns its text), `page.toast_action("Undo")` |
| element state | `web.exists(loc)`, `web.is_checked(loc)`, `web.is_enabled(loc)`, `web.attr(loc, "x")` |
| text in the browser UI | `native.wait_text("(?i)regex")`, `native.exists("<key>")` |
| wait for anything | `web.wait_until(lambda: ..., message="what is awaited")` |
| clipboard | `from pywinauto import clipboard`; `clipboard.EmptyClipboard()` before the copy; then `web.wait_until(lambda: clip() == expected)` with `clip()` returning `clipboard.GetData()`, or `""` when it raises (empty clipboard) |
