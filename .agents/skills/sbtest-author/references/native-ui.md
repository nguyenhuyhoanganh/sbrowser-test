# `native`: the browser's own UI and Windows

## The ui map `config/native_ui.yaml`

`python -m sbtest.tools.uia_dump` prints lines like
`Button 'Bookmarks' auto_id='view_1023' class='BookmarksButton'`. Copy the stable parts into the
ui map and use the key in tests and page objects:

```yaml
bookmarks_button:
  class_name: BookmarksButton          # class names stay the same between builds
addons_menu_pin:                       # native.click("addons_menu_pin", name="X") fills {name}
  control_type: Button
  title: "Pin {name}"
dialogs:
  bookmark_added: "(?i)page bookmarked|bookmark added to"
```

Criteria keys: `title`, `title_re`, `control_type`, `auto_id`, `class_name`, `class_name_re`,
`found_index`. Prefer `control_type` + `title_re` over `found_index`. Never use
`auto_id: view_NNN`: that number changes between builds. The browser runs in English
(`--lang=en-US`); Samsung's labels differ from Chrome's, so check them on the build.

## API

```python
native.hotkey("^d")                # browser shortcut; ^ Ctrl, + Shift, % Alt; {ENTER} {ESC} {TAB} {F5} {DELETE}
native.type_text("literal text")   # into the element that has the focus
native.click("bookmark_star")      # ui-map key or a criteria dict
native.click(criteria, in_main=False)   # an element in another browser window (add-on popup)
native.element("omnibox") / native.exists("downloads_button")
native.navigate(url)               # Ctrl+L, type the URL, Enter
native.omnibox_text()              # the URL the address bar shows
native.focus_page()                # moves the keyboard focus from the address bar into the page
native.close_download_bubble()     # closes the Downloads bubble that opens after a download
native.tab_titles()
native.menu("Bookmarks", "Bookmark manager")   # app menu path; each item matched by prefix
native.menu_items() / native.select_menu_items("Open in new tab")   # in an open menu
native.context_menu_web(web, "#next", "Open in new tab")            # right-click on a page element

dlg = native.wait_dialog("bookmark_added")     # a key of "dialogs" or a regex
dlg.texts() / dlg.text() / dlg.title
dlg.click("Done") / dlg.click_any("Allow", "Allow while visiting") / dlg.set_checkbox("Show bookmarks bar", True)
dlg.set_text("x") / dlg.set_text("x", title_re="(?i)user")
dlg.press("{ESC}") / dlg.close() / dlg.wait_closed()
native.wait_dialog_gone("bookmark_added")

fd = native.file_dialog("save"); fd.save_as(tmp_path / "page.html")   # also answers "replace?"
fd = native.file_dialog("open"); fd.open(file) / fd.open(f1, f2) / fd.cancel()
fd.select_folder(folder)           # "Load unpacked", "Change download location"

win = native.wait_explorer("Downloads")         # a File Explorer window
native.explorer_has_selected(win, "a.txt")
native.wait_text(r"(?i)bookmark added") / native.has_text(r"(?i)downloading")
native.wait_os_toast(r"(?i)notification text")

native.click_web_element(web, loc) / native.drag_web_element(web, src, dst)   # real mouse in the page
native.drag_web_to_ui(web, "#link", "bookmarks_bar")
native.drag_file_from_explorer(path, web=web, target=loc)
native.screenshot(path) / native.dump(path)
```
