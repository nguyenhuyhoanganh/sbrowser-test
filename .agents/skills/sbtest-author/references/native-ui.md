# Native layer (`native`) - pywinauto, UIA backend, Windows only

Use it for everything outside web content. Mark the test `@pytest.mark.native`; the
`native` fixture skips the test automatically where it cannot work (Linux, headless,
pywinauto missing).

## Contents

- The ui map `config/native_ui.yaml`
- API
- Traps

## The ui map `config/native_ui.yaml`

Find names with `python -m sbtest.tools.uia_dump` (`references/debugging.md`, "Exploring"),
put stable criteria into the ui map and use the logical name:

```yaml
bookmarks_button:
  class_name: BookmarksButton          # Views class names are stable
addons_menu_pin:                       # {name} is filled by native.click("addons_menu_pin", name="X")
  control_type: Button
  title: "Pin {name}"
dialogs:
  bookmark_added: "(?i)page bookmarked|bookmark added to"
```

Never use `auto_id='view_NNN'`: Chromium numbers its views in creation order, so the
number changes between builds and states. Ids from WebUI pages (`createFolderButton`) are fine.

Criteria keys: `title`, `title_re`, `control_type`, `auto_id`, `class_name`, `class_name_re`
(regex, e.g. a class renamed between builds: `"^(StarView|PageActionView)$"`), `found_index`.
Prefer `control_type` + `title_re` (case-insensitive) over `found_index`. Samsung's UI
strings can differ from Chromium's - always verify on the real build; locale of the
browser is forced to en-US by `--lang=en-US` in config.

## API

```python
native.hotkey("^d")            # browser shortcut (focuses the frame first). ^ Ctrl, + Shift, % Alt
native.hotkey("^+{DELETE}")    # Ctrl+Shift+Del ; {ENTER} {ESC} {TAB} {F5} {DOWN}
native.type_text("literal text")
native.click("bookmark_star")  # logical name from config/native_ui.yaml, or a criteria dict
native.click(criteria, in_main=False)   # an element in another browser window (add-on popup)
native.element("omnibox") / native.exists("downloads_button")
native.navigate(url)           # Ctrl+L, type, Enter - like a user in the address bar
native.focus_page()            # focus out of the omnibox into the page
native.close_download_bubble() # X of the Downloads bubble that opens after a download
native.omnibox_text()
native.tab_titles()
native.menu("Bookmarks", "Bookmark manager")   # app menu path (regex prefix per item)
native.select_menu_items("Open in new tab")   # in an already open native menu
native.menu_items()            # names in the open menu(s)
native.context_menu_web(web, "#next", "Open in new tab")   # real right click on DOM element

dlg = native.wait_dialog("bookmark_added")     # logical name (native_ui map "dialogs") or regex
dlg.texts() / dlg.text() / dlg.title
dlg.click("Done") / dlg.click_any("Allow while visiting", "Allow") / dlg.set_checkbox("Show bookmarks bar", True)
dlg.set_text("x") (first Edit) / dlg.set_text("x", title_re="(?i)user") / dlg.set_text("x", auto_id="..")
dlg.press("{ESC}") / dlg.close() / dlg.wait_closed() / dlg.dump()
native.wait_dialog_gone("bookmark_added")      # before clicking what a toast/bubble is anchored to

fd = native.file_dialog("save")   # Windows common dialog opened by the browser
fd.save_as(tmp_path / "page.html")  # handles "replace?" confirmation
fd = native.file_dialog("open"); fd.open(file) / fd.open(f1, f2) / fd.cancel()
fd.select_folder(folder)            # "Load unpacked", "Change download location"

native.wait_explorer("Downloads")         # File Explorer window (e.g. after "Show in folder")
native.explorer_has_selected(explorer, "a.txt")   # selected? (extension may be hidden)
native.wait_text(r"(?i)bookmark added")   # any element name in any browser window
native.has_text(r"(?i)downloading")
native.wait_os_toast(r"(?i)sbtest notification")

native.click_web_element(web, loc)        # real mouse click on a DOM element
native.drag_web_element(web, src, dst)    # real mouse drag inside the page
native.drag_web_to_ui(web, "#link", "bookmarks_bar")
native.drag((x1, y1), (x2, y2))
native.drag_file_from_explorer(path, web=web, target=loc)   # real OS file drag (e.g. .crx onto add-ons page)
native.screenshot(path) / native.dump(path) / native.close_stray_dialogs()
```

## Traps

- Native input needs the browser window in the foreground on an unlocked desktop (not a
  minimized RDP session). Shortcuts bring the browser back first; typing fails with "keyboard
  input would go to <process>" when another window is in front.
- The framework finds windows by the browser's PID: never run a second Samsung Browser by
  hand on the same profile.
- Every native click waits until the element is enabled, on screen and still - no sleeps.
  Browser bubbles also ignore clicks right after they show: `Dialog.click` waits that out and
  uses the real mouse (UIA Invoke only for Win32 buttons).
- Menus are separate top-level windows of the browser process; `select_menu_items` searches
  all of them.
- A dialog is not found -> `native.dump("artifacts/uia_now.txt")` right before the wait.
- Product traps of each feature (star, toasts, download bubble...): `references/feature-notes.md`.
