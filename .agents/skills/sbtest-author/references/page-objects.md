# Page objects

```
sbtest/pages/base.py        BasePage - helpers for Samsung's si-* components, shared by every page
sbtest/pages/bookmarks.py   history.py   downloads.py   extensions.py   (internal pages)
sbtest/pages/webstore.py    Chrome Web Store item page (public site)
```

Tests only use the `pages` fixture (`pages.extensions`, ...). Page objects hold selectors and
page steps, **no assertions**: they return data and wait for their own effect. Each module
docstring has a STATUS line (`verified on Samsung Browser <version> (Chromium <n>)`) and how
the page differs from upstream Chromium. What each method does: `references/action-catalog.md`
or the class itself.

Every page object has the same layout - keep it when adding a method:

1. selectors (class constants) at the top;
2. read - returns data, changes nothing (`titles()`, `rows()`, `is_selected(x)`);
3. wait - `wait_item(x)`, `wait_titles([...])`;
4. actions - one method per user action, named after what the user does (`pause(name)`,
   `sort_by_name()`), docstring = the UI path and what it returns; it waits for its own
   effect (the row gone, the dialog closed, the new tab) before it returns.

A new action: one method in the right section, built from `web.*` / BasePage helpers (they
frame the interaction for `--screenshot-steps` / `--record`), run once on the build, then a
row in `references/action-catalog.md`.

A page changed after an update: `references/debugging.md`, "When a page or the browser UI
changed" - keep method names, parameters and return types so tests do not change.

Private APIs: `ExtensionsPage.info()` uses `chrome.developerPrivate` (works on Samsung 31);
if a build stops exposing it, check `web.js("return typeof chrome.developerPrivate")` and
switch to a UI-based read.

Selectors: `references/web-api.md`, "Locators".

## BasePage helpers

| method | for |
|--------|-----|
| `open(subpath="")` / `wait_loaded()` / `is_open()` / `url` | navigation (URL from config `pages`) |
| `search(text)` / `clear_search()` / `side_bar("Image")` | side bar search field and filters |
| `find_by_text(css, text, contains=False, within=None)` | visible element of `css` with that text, any shadow depth |
| `click_text(text, css=..., within=None)` | buttons/links/menu items by label |
| `toolbar("Delete")` / `toolbar_any("Delete", "Delete all")` / `toolbar_labels()` / `toolbar_enabled(label)` / `cancel_selection()` | page toolbar (labels change with the selection) |
| `menu_items()` / `click_menu_item(text)` / `choose_menu_item("Open all")` | open menu (right click, ⋮); `choose_menu_item` waits and matches a prefix |
| `wait_toast(contains="")` / `toast_action("Undo")` / `toast_element()` | snack bar |
| `open_dialog()` / `dialog_text()` / `dialog_input(id)` / `dialog_button(text)` / `wait_dialog_closed()` / `has_dialog()` | in-page dialog |
| `confirm_dialog_if_open("Delete", "OK")` / `answer_dialog_if_open(confirm, labels)` | a confirmation that may or may not show |
| `q(value)` | quote for CSS attribute selectors: `f"[aria-label={q(name)}]"` |

## Adding a new page

1. Path key in `config/default.yaml` -> `pages:` (navigation uses `chrome://<path>`, the
   address bar shows `internet://<path>`).
2. `sbtest/pages/<name>.py`: `class XPage(BasePage)` with `page`, `ROOT` and the page's steps.
3. Register it in `PAGE_CLASSES` and `__all__` (`sbtest/pages/__init__.py`).
4. Reading lists: one JS call over the rows (see `HistoryPage.rows`, `DownloadsPage.info`) -
   lists re-render and per-row calls go stale. A list that reuses its row elements (downloads)
   can show another entry in the same element a moment later: confirm the row still shows
   what you look for before acting on it (`DownloadsPage.item`).
