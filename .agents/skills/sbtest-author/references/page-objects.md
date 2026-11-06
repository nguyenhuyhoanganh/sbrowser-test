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
| `search(text)` / `clear_search()` | toolbar search field (`SEARCH_INPUT`) |
| `find_by_text(css, text, contains=False, within=None)` | visible element of `css` with that text, any shadow depth |
| `click_text(text, css=..., within=None)` | buttons/links/menu items by label |
| `click_menu_item(text)` | item of the open action menu |
| `wait_toast(contains="")` / `toast_action("Undo")` | toast |
| `open_dialog()` / `dialog_text()` / `dialog_input(id)` / `dialog_button(text)` / `wait_dialog_closed()` | in-page dialog |
| `q(value)` | quote for CSS attribute selectors: `f"[aria-label={q(name)}]"` |

## Adding a new page

1. Path key in `config/default.yaml` -> `pages:` (navigation uses `chrome://<path>`, the
   address bar shows `internet://<path>`).
2. `sbtest/pages/<name>.py`: `class XPage(BasePage)` with `page`, `ROOT` and the page's steps.
3. Register it in `PAGE_CLASSES` and `__all__` (`sbtest/pages/__init__.py`).
4. Reading lists: one JS call over the rows (see `HistoryPage.rows`, `DownloadsPage.info`) -
   lists re-render and per-row calls go stale.
