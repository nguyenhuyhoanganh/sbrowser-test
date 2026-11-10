# Feature notes: product behaviour and known problems

This file is the only place that records how the product behaves. When a build behaves
differently: report it, and change the note here after the user confirms it.

## Contents

- Whole product
- Bookmarks (prefix BM)
- History (prefix HIS)
- Downloads (prefix DL)
- Add-ons (prefix ADD)
- General browsing (prefix GEN)

## Whole product

- Terms: **snack bar** = the bar inside an internal page ("1 bookmark deleted" [Undo]);
  **toast** = the small popup of the browser itself ("Page bookmarked." [Edit]); **bubble** =
  any other popup window of the browser.
- Internal pages open as `chrome://<page>`; the address bar shows `internet://<page>`.
  `web.open("internet://...")` fails; typing `internet://...` in the address bar works.
- Pages, shortcuts and links that open "a page" open it in a NEW TAB.
- Internal pages share Samsung's `si-*` components: toolbar buttons, snack bar, `si-dialog`,
  right-click menu, a left side bar with search and filters.
- The address bar is a UIA Group named "Address and search bar, <url>".
- A click on the element a toast points to (the star under "Page bookmarked.") only closes the
  toast; the click has no other effect while the toast is open.
- The app menu button is "Samsung Browser"; its item names end with the shortcut ("Downloads
  Ctrl+J").
- The browser can crash while it closes (`session.restart()` raises `BrowserCrashed`). Changes
  it had not saved are lost, e.g. a bookmark edited less than 2.5 s before. This is a product
  regression, not a test problem.

## Bookmarks (prefix BM)

- Tree roots: "PC bookmarks" > "Bookmark bar"; the tree is always expanded. Each row has a
  round check box. Edit, Share, Delete and Select all are toolbar buttons that act on the
  selected rows; with all rows selected they read "Delete all" and "Deselect all".
- Right-click on a row: Edit, Delete, Open all (n) in new tab / new window / Secret mode.
- Right ⋮ menu: Add bookmark (the same dialog as Edit), Sort by name (folders first, then A-Z),
  Open all (n) in new tabs / new window / Secret mode. n is the number of SELECTED rows.
- Left ⋮ menu: Create folder in selected folder, Sort by name, Import bookmarks (Settings in a
  new tab), Export bookmarks (Windows Save As, HTML file).
- "Create folder" adds "Folder N", opens it and puts its name into edit mode in the tree.
- Delete has no confirmation: the snack bar "1 bookmark deleted" with Undo shows at once.
- Clicking a bookmark opens it in a new tab.
- Drag and drop inside the manager works only with `method="native"` (the real mouse).
- The toolbar "Bookmarks" button opens a panel with Add bookmark (adds the current page),
  Create folder and Expand (opens the manager), and the tree "PC bookmarks" > "Bookmark bar".
- Ctrl+D bookmarks the page at once and shows the toast "Page bookmarked." [Edit] ("Bookmark
  added to <folder>" when the page is already bookmarked in another folder). The star then
  reads "Remove from Bookmarks".
- The star is shown only while the address bar does not have the keyboard focus. `web.open`
  leaves the focus in the address bar, and when the toast closes the focus returns to the
  address bar a moment later.
- The toast closes by itself after a few seconds, so its Edit button must be clicked at once.
- Toast Edit opens the dialog "Edit bookmark": fields "Name" and "Web address" (the address
  without `http://`), buttons Save and Cancel.

## History (prefix HIS)

- Entries are listed newest first, grouped by day; only the first row of a day shows the day
  header.
- Each row has a round check box; the day header has its own check box. Toolbar: Share,
  Delete, Clear history. Delete and Clear history have no confirmation.
- There is no ⋮ button per row. Right-click on a row: Open all (1) in new tab / new window /
  Secret mode, More results from same site (the list then shows only that site), Copy link,
  Delete, Inspect.
- The time filters in the side bar are check boxes: the selected ranges add up.
- "Clear browsing data" opens Settings `clearBrowserData` in a new tab.
- The search filters the list after a short delay.

## Downloads (prefix DL)

- Each test downloads into its own folder (`downloads_dir`) without a Save As dialog.
- Side bar: search and the categories All, Image, Video, Audio, Document, Others. The search
  also matches the file's folder path, so search for a part of the name that no folder name
  contains ("ta.bin", not "data").
- A finished row shows name, size ("2.05 KB"), source link and the icons Copy link, Show in
  folder and X. X removes the row from the list (the file stays on disk) and shows the snack
  bar "x removed from Downloads." with Undo; Undo puts the row back. A row in progress shows a progress bar and the
  buttons Pause / Resume and Cancel. Cancel removes the row ("x removed from Downloads." with
  Undo); the toolbar Downloads bubble then shows "Canceled". Toolbar: "Clear download history"
  (cases call it "Clear all").
- The list reuses its row elements when its content changes: an element kept from an earlier
  read can show another file.
- A finished download opens the Downloads bubble, which can cover the page's toolbar.
- "Show in folder" opens a File Explorer window, which the test must close.
- Dangerous file types show a warning instead of finishing.

## Add-ons (prefix ADD)

- Page title "Add-ons". Developer mode is a toggle in the LEFT side bar; when it is on, the
  toolbar shows Load Unpacked, Pack add-on, Update, and each card shows its version. Card
  buttons: Details, Remove. Remove opens the browser prompt "Delete <name>?" [Remove] [Cancel].
- The toggle of a card does not prove that the add-on works: check its effect on a page (the
  sample add-on sets `data-sb-addon="active"`).
- Details opens the same page with `?id=...` in the URL.
- Web Store: the item page button reads "Add to Chrome" or "Install"; then the prompt
  'Add "<name>"?' [Add] [Not now]. The store also shows a "Switch to Chrome?" bubble, which the
  test ignores. Only free add-ons, and only through the company proxy.
- Toolbar "Add-ons" (puzzle icon) menu: per add-on "Pin <name>" / "Unpin <name>" and "More
  options for <name>" (Options, Remove from Samsung Browser, Manage add-on, View web
  permissions). The popup of a pinned add-on is readable through UIA.
- "Options" opens the options page in a BACKGROUND tab.

## General browsing (prefix GEN)

- Right-click on a link: "Open in new tab" (not "Open link in new tab"), "Open in new window",
  "Open in Secret mode", "Open in side panel", "Save link as", "Copy link", "Share link",
  "Inspect". "Open in new tab" opens the tab in the background: the current tab stays in front.
- Pages opened by `window.open` are windows; they are listed in `web.tabs` too.
- "Leave site?" (beforeunload) is shown only after the user clicked in the page.
