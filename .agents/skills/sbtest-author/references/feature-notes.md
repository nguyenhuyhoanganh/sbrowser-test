# Feature notes (what works, what bites)

The one place for the product's traps; other references only point here. What a build does
differently from these notes: report it and let the user verify it, then record it here.

## Contents

- Whole product
- Bookmarks (`internet://bookmarks`, prefix BM)
- History (`internet://history`, prefix HIS)
- Downloads (`internet://downloads`, prefix DL)
- Add-ons (`internet://extensions`, prefix ADD)
- General browsing (prefix GEN)

## Whole product

- **These notes were verified on Samsung Browser 31.0.1.40 with the earlier Selenium web
  layer.** The web layer is Playwright now (attached over DevTools) and has not run on a
  Samsung build yet: what a note says about the *product* still holds; what it says about
  the web layer's limits (background tabs, the home page) has to be checked again - report
  what differs.
- URLs opened by `web.open` are `chrome://...` (`pages.scheme: chrome`); the address bar *shows*
  `internet://...` (`pages.display_scheme`, `cfg.display_url(name)` for omnibox asserts).
  `web.open("internet://...")` does nothing; typing it in the omnibox (`native.navigate`) works.
- The framework starts the exe itself with `--remote-debugging-port` and Playwright attaches
  to it; nothing has to match the build's Chromium version. Samsung blocks DevTools on the
  home page (newtab): never use it as a start page.
- Fresh profiles may show a "Samsung Browser has been updated." bubble (some starts only):
  nothing waits for it - one quick look after start, then for 10 s every native action first
  closes it if it has shown up (`startup_bubbles` in `config/native_ui.yaml`,
  `native.startup_bubble_watch`). Web-only tests are not affected.
- A click on the button a bubble/toast is anchored to (the star under "Page bookmarked.") only
  closes the bubble: `native.wait_dialog_gone("bookmark_added")` first.
- The address bar is a Group named "Address and search bar, <url>" (no Edit control): read it
  with `native.omnibox_text()`.
- Bubbles with no title are found by a Text inside.
- Terms used in these skills: **snack bar** = the in-page si-snack-bar ("1 bookmark deleted"
  [Undo], `page.wait_toast`); **toast** = the native browser toast ("Page bookmarked." [Edit],
  `native.wait_dialog`); **bubble** = any other native popup window of the browser.
- Internal pages share `si-*` components: toolbar buttons (`page.toolbar("Delete")`),
  snack bar (`page.wait_toast("deleted")`), `si-dialog`, right-click `si-action-menu`,
  left side bar with search + filters (`page.side_bar("Image")`).
- Pages, shortcuts and links that open "a page" open it in a NEW TAB:
  `web.switch_tab(url=cfg.page_url("history"))`.
- Samsung 31.0.1.40 crashes on exit about 1 time in 3 under load (exit code 0x80000003, a CHECK in
  `partition_alloc_support.cc`), also when the window is closed like a user; what it had not
  saved yet is lost (a bookmark edited < 2.5 s before closing). `session.restart()` then fails
  with `BrowserCrashed`.
- App menu button is "Samsung Browser"; its items carry the shortcut in the name
  ("Downloads Ctrl+J") - `native.menu("Downloads")` matches by prefix.

## Bookmarks (`internet://bookmarks`, prefix BM)

- Seed with `@pytest.mark.browser(bookmarks=...)`.
- Roots "PC bookmarks" > "Bookmark bar"; the tree is expanded. Rows have a round check box;
  Edit / Share / Delete / Select all are toolbar buttons acting on the selection ("Delete all" /
  "Deselect all" when everything is selected).
- Right click a row: Edit, Delete, Open all (n) in new tab / new window / Secret mode.
  Right ⋮: Add bookmark (`add_bookmark`, same dialog as Edit), Sort by name (folders first),
  Open all (n) in new tabs / new window / Secret mode - n counts the SELECTED rows ("Open
  all (0)" with nothing selected; `open_all()` selects first). Left ⋮: Create folder in selected folder, Sort by name, Import bookmarks (opens
  Settings in a new tab), Export bookmarks (Save As, HTML: `export(native, path)`).
- "Create folder" adds "Folder N" in the selected folder, opens it and edits its name in the
  tree (`add_folder(name)` types over it). Delete is immediate: snack bar "1 bookmark deleted"
  + Undo. Clicking a bookmark opens it in a NEW TAB.
- Import/Export use Windows file dialogs -> `native.file_dialog("open"/"save")`; import file:
  `files.bookmarks_html(...)`.
- Drag & drop inside the manager: `method="native"` (real mouse) is the reliable option;
  synthesized `html5` events are ignored there.
- Toolbar "Bookmarks" button -> panel: header buttons Add bookmark (adds the current page),
  Create folder, Expand (opens the manager); tree "PC bookmarks" > "Bookmark bar" (folders are
  Buttons `auto_id=folder`, bookmarks are TreeItems). Ui-map keys `bookmarks_panel_*`.
- Ctrl+D bookmarks at once: toast "Page bookmarked." [Edit] (`dialogs.bookmark_added`), no
  bubble; the star becomes "Remove from Bookmarks" (clicking it removes the bookmark, once
  the toast is gone - see "Whole product").
- The star (class `StarView` or `PageActionView` depending on the build; the ui map matches
  both) only shows when the omnibox has NO focus. A page opened by `web.open` leaves the focus there, and when
  the "Page bookmarked." toast closes the focus goes back to the omnibox a moment later: call
  `native.focus_page()` after opening the page and before Ctrl+D, and before a star check wait
  until the star shows, focusing the page again while it does not.
- The "Page bookmarked." toast closes by itself after a few seconds: click its "Edit" right
  away (no `focus_page()` or long star wait in between; check the star with `native.exists`).
- Toast "Edit" -> an "Edit bookmark" dialog (cases may call it a bubble): fields read "Name" /
  "Web address" on screen, their UIA names are
  "Bookmark name" / "Bookmark URL" (ui map `bookmark_edit_name` / `_url`; URL shown without
  `http://`), "Create folder in selected folder", Save / Cancel. Toast text is "Page
  bookmarked." or "Bookmark added to <folder>" (page already bookmarked elsewhere).

## History (`internet://history`, prefix HIS)

- Seed by visiting `site.page(title)`; wait for the title before the next visit.
- Entries are newest first, grouped by day; `rows()` reads them in one call.
- Each row has a round check box (`select()`), the day header has its own (`select_day()`).
  Every row carries a day header; only the first row of a day (attribute `is-card-start`)
  shows it - `rows()` / `days()` read only those.
  Toolbar: Share, Delete, Clear history - both delete at once, no confirmation.
- No ⋮ per row: right click -> Open all (1) in new tab / new window / Secret mode, More
  results from same site (the list then shows `?q=<host>`), Copy link, Delete, Inspect.
- Side bar time filters are CHECK BOXES (several ranges add up): `filter_time("Last hour")`
  leaves exactly the given ones ticked. "Clear browsing data" -> settings `clearBrowserData`
  in a new tab.
- Search is debounced; wait on the result (`web.wait_until(lambda: h.titles() == [...])`).
- Ctrl+H is a browser shortcut -> `native.hotkey("^h")`, opens a new tab.

## Downloads (`internet://downloads`, prefix DL)

- The session downloads into its own folder (`downloads_dir`); prompt is off by default.
  Turn on Save As with `browser(prefs={"download.prompt_for_download": True})` + native `file_dialog`.
- Side bar search + categories (All, Image, Video, Audio, Document, Others: `filter_category()`).
  The search also matches the file's folder path: search a part of the name no folder has
  ("ta.bin", not "data" - the downloads folder can be under AppData or D:\data).
- Finished row: name, size ("2.05 KB"), source link, icons "Copy link", "Show in folder",
  X (remove, snack bar + Undo). In-progress row: progress bar + text buttons Pause/Resume,
  Cancel (`pause(name)`, `cancel(name)`). Cancel REMOVES the row ("x removed from Downloads." + Undo);
  the toolbar Downloads bubble shows "Canceled". Toolbar: "Clear download history".
- The list reuses its row elements when it re-renders (a download added, removed, restored
  by Undo): an element found for "a.txt" can show "b.bin" a moment later. `item()` confirms
  the row before an action uses it; read rows through the page object, not a kept element.
- A finished download opens the toolbar Downloads bubble over the page. On some builds it
  covers the downloads page's toolbar button "Clear download history" (cases call it "Clear
  all"): any test that downloads and then uses that toolbar first calls
  `native.close_download_bubble()` (its X, ui map `download_bubble_close`; the test is
  `native`).
- "Show in folder"/"Open" launch Explorer / the default app (outside the browser): assert with
  `native.wait_explorer(...)` and close the window afterwards.
- Dangerous/blocked file types show a warning instead of finishing - pick safe types.

## Add-ons (`internet://extensions`, prefix ADD)

- Page title "Add-ons". Developer mode is a toggle in the LEFT side bar; on, the toolbar shows
  Load Unpacked, Pack add-on, Update and cards show the version. Card buttons Details / Remove
  (si-flat-button). Remove -> native bubble 'Delete <name>?' [Remove] [Cancel].
- Install prompt (store) -> 'Add "<name>"?' [Add] [Not now]; the store also shows
  Google's "Switch to Chrome?" bubble (ignore it). App menu has "Add-ons".
- Load with `browser(extensions=["sample_addon"])` (unpacked). `info()` returns state from
  `chrome.developerPrivate` (`ENABLED`/`DISABLED`).
- Prove an add-on is active through its effect on a page (content script attribute), not
  only through the toggle.
- Details: `open_details(name)` -> URL `?id=...`; read with `web.wait_page_text`.
- Install flows (all native):
  - Load unpacked: `pages.extensions.load_unpacked(native, folder)` (dev mode, button,
    Windows folder picker).
  - Web Store: `pages.webstore.install(ext_id, native)` - through the company proxy; button
    text from config `webstore.add_button_texts`; free extensions with a small install prompt only
    (Google Scholar Button in `resources/data/addons.yaml`). The store button reads "Add to
    Chrome" on some item pages and "Install" on others (both in the config).
- Toolbar "Add-ons" (puzzle, `ExtensionsToolbarButton`) -> menu: each add-on with "Pin <name>" /
  "Unpin <name>" and "More options for <name>" (menu: Options, Remove from Samsung Browser,
  Manage add-on, View web permissions). Pinned icon = `ToolbarActionView` named
  "<name>\nHas access to this site"; its popup is a Document readable through UIA.
- "Options" opens the add-on's options page in a BACKGROUND tab: the web layer could not read that
  chrome-extension:// tab with Selenium (renderer timeout; not tried with Playwright yet) - check `native.tab_titles()`, bring it to front
  by clicking its TabItem and read it with `native.wait_text(...)`.

## General browsing (prefix GEN)

- Tabs opened by the page: capture `before = web.tabs` first, then `web.wait_new_tab(before)`.
- Link right-click menu (native): "Open in new tab" (not Chrome's "Open link in new tab"),
  "Open in new window", "Open in Secret mode", "Open in side panel", "Save link as", "Copy link",
  "Share link", "Inspect". "Open in new tab" opens it in the BACKGROUND: the current tab stays.
- `window.open` popups are windows; they also appear in `web.tabs`.
- `beforeunload` "Leave site?": `with web.dialog(accept=False) as d:` around the navigation
  stays on the page (`d.type == "beforeunload"`), `accept=True` leaves. Proven on plain
  Chromium (`tests/framework/test_live.py`), not on a Samsung build yet; the page needs a
  click first (browsers only ask after a user gesture).
