# Web layer API (`web`)

Built on Playwright, attached over DevTools to the browser the session started. Every method
takes a **locator string** or an element (what `web.find` returns). Every finder waits
(default `timeouts.default` = 10 s) for a *visible* element unless said otherwise. Every
command to the page gives up after `timeouts.command` (30 s) with a `TimeoutError`: a page
blocked by a modal browser UI fails the step instead of hanging the run.

## Contents

- Locators
- Waits (never sleep)
- Actions
- Reading
- Tabs, windows, iframes, misc
- JavaScript dialogs
- Playwright itself

## Locators

| Syntax | Meaning |
|--------|---------|
| `"#id .cls"` / `"css=..."` | CSS; it **pierces open shadow roots** (every internal page is built from them) |
| `"a-app >>> #toolbar >>> input"` | **path**: each `>>>` continues inside what matched before, its shadow root included - use it to say *which* `#toolbar` |
| `"deepcss=si-snack-bar"` | the same as plain CSS (says "anywhere on the page") |
| `"xpath=//a"` or `"//a"` | XPath (light DOM only) |
| `"id=x"`, `"name=q"` | attribute shortcuts |
| `"text=Delete"` | smallest element whose text is exactly `Delete` (case-sensitive) |
| `"text~=deleted"` | text contains, case-insensitive |
| `"aria=Search bookmarks"` | `aria-label` / `title` / `placeholder` / `label` equals |
| `'role=button[name="Save"]'` | accessible role + name (Playwright role selector) - the names `aria.yaml` / `dom --aria` show |
| `"pw=<selector>"` | any other Playwright selector, as is |

Scoping: `web.find("deep=#menuButton", within=row)` searches **inside row** (its shadow root
included), with every syntax.

Take locators from `python -m sbtest.tools.dom <page>` (`references/debugging.md`,
"Exploring"), not from memory. Prefer ids (`#saveButton`) and stable tags (`bookmarks-item`);
where only `:nth-of-type` would work, use a text, aria or role lookup. Never generated class
names (`css-1x2y3z`).

## Waits (never sleep)

```python
web.find(loc, timeout=None, visible=True, within=None)  # -> element
web.find_all(loc, visible=True, within=None)            # no wait, may be []
web.wait_visible(loc) / web.wait_present(loc) / web.wait_gone(loc)
web.wait_count(loc, 3)
web.wait_text(loc, "Saved", contains=True)
web.wait_page_text("Saved")            # anywhere on the page incl. shadow DOM
web.wait_url("/echo") / web.wait_title("Static page 2") / web.wait_ready()
web.wait_until(lambda: pages.bookmarks.titles() == ["A", "B"], message="A,B listed")
web.wait_file(downloads_dir, "*.pdf", timeout=web.long_timeout)
```

## Actions

```python
web.click(loc)                 # scrolls into view; waits until visible, still and enabled; JS-click fallback when covered
web.js_click(loc)              # force (hidden or covered elements)
web.double_click(loc) / web.right_click(loc) / web.hover(loc)
web.type(loc, "text", clear=True, enter=False)   # key by key
web.clear(loc) / web.set_value(loc, "v")      # set_value: JS + input/change events
web.press("ENTER") / web.press(Keys.CONTROL, "a") / web.press("TAB", loc="#name")   # from sbtest.web import Keys
web.type_keys("text", enter=False)  # into the element that has the focus (a field the page focused itself)
web.select("#color", text="Blue")  # native <select> (also value=/index=)
web.set_checked(loc, True)         # checkbox, si-select, si-toggle, radio
web.drag_and_drop(src, dst, method="actions"|"html5"|"native")
web.drag_by(loc, dx, dy)
web.upload("#file", path1, path2)  # input[type=file], no OS dialog
web.scroll_to(loc) / web.scroll_by(0, 600)
```

A click waits `timeouts.action` (5 s) for its element to be ready, then clicks through
JavaScript; `web.click(loc, js_fallback=False)` raises instead.

Typing into a component that wraps its input (`si-input`): target the inner input:
`"... >>> #name >>> #input"` or page-object helpers (`page.dialog_input("name")`).

Drag & drop choice: `html5` for `draggable=true` + dataTransfer pages; `actions` for
mouse-event based widgets/sortables; `native` (real mouse, Windows) for anything that
must cross into browser UI or when the other two do not trigger the app's handlers.

## Reading

```python
web.text(loc)          # text as shown (includes the element's shadow content)
web.texts(loc)         # list for all visible matches
web.page_text()        # everything visible on the page, shadow DOM included
web.attr(loc, "href")  # the attribute as written in the markup (None when absent)
web.prop(loc, "checked") / web.value(loc)   # live state of a control
web.exists(loc) / web.is_visible(loc) / web.count(loc) / web.is_enabled(loc) / web.is_checked(loc)
web.table("table#t")   # [{header: cell}]
web.focused()          # deepest active element
web.same_element(a, b) # two elements are the same DOM node (they never compare equal with ==)
web.aria_snapshot()    # accessibility tree of the page (or of loc) as YAML: roles, names, states
web.html()             # markup of the page (light DOM)
web.url / web.title / web.tabs
```

## Tabs, windows, iframes, misc

```python
before = web.tabs; web.click("#blank-link"); web.wait_new_tab(before)   # switches to it
web.switch_tab(index=0) / web.switch_tab(title="History") / web.switch_tab(url="settings")
web.new_tab(url) / web.close_tab()
web.js("return arguments[0].value", el)   # function body; elements in and out; a Promise is awaited
web.cdp("Page.getLayoutMetrics") / web.screenshot(path)
web.open(url) / web.open_internal("history") / web.back() / web.forward() / web.refresh()
web.open(url, blocking=False)    # navigation that stops at a browser prompt (HTTP sign-in)
with web.frame("#iframe"):       # inside an iframe, back to the page afterwards
    web.click("#inner-button")
```

`web.tabs` are the open tabs and popup windows, oldest first; `web.page` is the current one.
A tab the browser opens in the background is in `web.tabs` too: `switch_tab` makes it the one
`web.*` talks to, it does not bring it to the front on screen.

The browser starts without a window: the test's first `web.open` (or `pages.x.open()`, or
`browser(start_page=...)`) opens the window directly on its page, without about:blank and
with Back off. Before that `web.tabs` is `[]` and `web.url` is `""`.

## JavaScript dialogs

alert / confirm / prompt / "Leave site?" block the page while open, so say how to answer
**before** the action that opens them:

```python
with web.dialog(accept=True, prompt_text="Ann") as d:   # accept=False = Cancel
    web.click("#prompt")
assert d.text == "Your name?"        # also d.type (alert | confirm | prompt | beforeunload), d.messages
```

Leaving the block waits for the dialog (`TimeoutError` when none showed;
`required=False` for one that may not come). A dialog no block expects is dismissed at once
(a "Leave site?" is accepted), logged, and kept in `web.dialogs` and the failure's
`console.txt`.

Browser-owned dialogs that are **not** JS dialogs (bubbles, permission prompts, Save As,
print preview, "Add extension?") are native: use `native`, not `web`.

## Playwright itself

`web.page` (current tab) and `web.context` are Playwright's async objects, for the rare
thing `web.*` does not cover; run their calls through `web.run`, which adds the timeout:

```python
pdf = web.run(web.page.pdf())
web.run(web.page.locator("role=button[name='Save']").click())
```

Interactions done this way are not framed in step pictures / videos; prefer `web.*`.
