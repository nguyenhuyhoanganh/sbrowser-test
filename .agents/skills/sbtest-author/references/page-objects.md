# Page objects

```
sbtest/pages/base.py        BasePage: helpers for Samsung's si-* components, shared by every page
sbtest/pages/bookmarks.py   history.py   downloads.py   extensions.py   (internal pages)
sbtest/pages/webstore.py    Chrome Web Store item page
```

Tests reach them through the `pages` fixture. A page object holds the selectors and the page's
steps and makes no assertions: it returns data and waits for its own effect.

Layout of every page object - keep it when adding a method:

1. selectors (class constants);
2. read - returns data, changes nothing (`titles()`, `rows()`, `is_selected(x)`);
3. wait - `wait_item(x)`, `wait_titles([...])`;
4. actions - one method per user action, named after it (`pause(name)`, `sort_by_name()`),
   docstring = the UI path and what it returns; it waits for its effect (row gone, dialog
   closed, new tab) before it returns.

A new action: one method in the right section, built from `web.*` and the BasePage helpers
(so step pictures and videos frame it), run once on the build, then a row in
`references/action-catalog.md`. A page that changed: keep method names, parameters and return
types so tests do not change.

## BasePage helpers

| method | for |
|---|---|
| `open(subpath="")` / `wait_loaded()` / `is_open()` / `url` | open the page (path from `pages:` in `config/default.yaml`) |
| `search(text)` / `clear_search()` / `side_bar("Image")` | side bar search and filters |
| `find_by_text(css, text, contains=False, within=None)` | visible element of `css` with that text, any shadow depth |
| `click_text(text, css=..., within=None)` | button, link or menu item by label |
| `toolbar("Delete")` / `toolbar_any("Delete", "Delete all")` / `toolbar_labels()` / `toolbar_enabled(label)` / `cancel_selection()` | page toolbar (labels change with the selection) |
| `menu_items()` / `click_menu_item(text)` / `choose_menu_item("Open all")` | an open menu; `choose_menu_item` waits and matches a prefix |
| `wait_toast(contains="")` / `toast_action("Undo")` / `toast_element()` | snack bar |
| `open_dialog()` / `dialog_text()` / `dialog_input(id)` / `dialog_button(text)` / `wait_dialog_closed()` / `has_dialog()` | in-page dialog |
| `confirm_dialog_if_open("Delete", "OK")` / `answer_dialog_if_open(confirm, labels)` | a confirmation that may or may not show |
| `q(value)` | quote a value for a CSS attribute selector: `f"[aria-label={q(name)}]"` |

## A new page

1. Its path in `config/default.yaml` -> `pages:` (opened as `chrome://<path>`).
2. `sbtest/pages/<name>.py`: `class XPage(BasePage)` with `page`, `ROOT` and its steps.
3. Register it in `PAGE_CLASSES` and `__all__` of `sbtest/pages/__init__.py`.
4. Read a list in one JS call over its rows (see `HistoryPage.rows`): lists re-render, and a
   list that reuses its row elements can show another entry in the same element a moment
   later - confirm the row before acting on it (see `DownloadsPage.item`).
