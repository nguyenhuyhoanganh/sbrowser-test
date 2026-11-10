# `web`: everything inside web content

Every method takes a locator string or an element (what `web.find` returns). Finders wait up
to 10 s for a visible element, then raise `TimeoutError`.

## Contents

- Locators
- Waits
- Actions
- Reading
- Tabs, navigation, iframes
- JavaScript dialogs

## Locators

| syntax | meaning |
|---|---|
| `"#id .cls"`, `"css=..."` | CSS; it reaches into shadow roots (internal pages are built from them) |
| `"bookmarks-app >>> #toolbar >>> input"` | path: each `>>>` searches inside the element matched before it |
| `"text=Delete"` | the smallest element whose text is exactly `Delete` |
| `"text~=deleted"` | text contains, case-insensitive |
| `"aria=Search bookmarks"` | `aria-label`, `title`, `placeholder` or `label` equals |
| `'role=button[name="Save"]'` | accessible role and name, as `dom --aria` prints them |
| `"xpath=//a"` | XPath (no shadow roots) |

`web.find("#menuButton", within=row)` searches inside `row`. Take locators from
`python -m sbtest.tools.dom <page> --interactive`, never from memory. Use ids and tag names;
where only `:nth-of-type` would work, use text, aria or role. Never use generated class
names.

## Waits

```python
web.find(loc, timeout=None, visible=True, within=None)   # -> element
web.find_all(loc, visible=True, within=None)             # no wait, may be []
web.wait_visible(loc) / web.wait_present(loc) / web.wait_gone(loc)
web.wait_count(loc, 3)
web.wait_text(loc, "Saved", contains=True)
web.wait_page_text("Saved")
web.wait_url("/echo") / web.wait_title("Static page 2") / web.wait_ready()
web.wait_until(lambda: bm.titles() == ["A", "B"], message="A, B listed")
web.wait_file(downloads_dir, "*.pdf", timeout=web.long_timeout)
```

## Actions

```python
web.click(loc)                      # waits until visible, not moving and enabled; covered for 5 s -> JS click
web.js_click(loc)                   # hidden or covered element
web.double_click(loc) / web.right_click(loc) / web.hover(loc)
web.type(loc, "text", clear=True, enter=False)
web.clear(loc) / web.set_value(loc, "v")   # set_value: for inputs that ignore typing
web.press("ENTER") / web.press(Keys.CONTROL, "a") / web.press("TAB", loc="#name")
web.type_keys("text", enter=False)  # into the element that already has the focus
web.select("#color", text="Blue")   # <select>; also value= / index=
web.set_checked(loc, True)          # checkbox, si-select, si-toggle, radio
web.drag_and_drop(src, dst, method="actions")   # "html5": draggable + dataTransfer pages; "native": real mouse
web.drag_by(loc, dx, dy)
web.upload("#file", path1, path2)   # <input type=file>, no Windows dialog
web.scroll_to(loc) / web.scroll_by(0, 600)
```

Typing into an `si-input`: target its inner input, `"... >>> #name >>> #input"`, or the page
object's `dialog_input("name")`.

## Reading

```python
web.text(loc) / web.texts(loc)      # text as shown, shadow content included
web.page_text()                     # all visible text of the page
web.attr(loc, "href")               # attribute as written (None when absent)
web.prop(loc, "checked") / web.value(loc)
web.exists(loc) / web.is_visible(loc) / web.count(loc) / web.is_enabled(loc) / web.is_checked(loc)
web.table("table#t")                # [{header: cell}]
web.aria_snapshot()                 # roles, names and states of the page as YAML
web.js("return arguments[0].value", el)   # a function body; elements in and out
web.url / web.title / web.tabs
```

## Tabs, navigation, iframes

```python
web.open(url) / web.back() / web.forward() / web.refresh()
web.open(url, blocking=False)       # a navigation that stops at a browser prompt (HTTP sign-in)
before = web.tabs; web.click("#blank-link"); web.wait_new_tab(before)   # switches to it
web.switch_tab(index=0) / web.switch_tab(title="History") / web.switch_tab(url="settings")
web.new_tab(url) / web.close_tab()
with web.frame("#inner"):
    web.click("#inner-button")
```

`web.tabs` lists tabs and popup windows, oldest first, background tabs included. `switch_tab`
makes `web.*` use another tab; it does not bring that tab to the front on screen. Before the
test opens its first page the browser has no window: `web.tabs` is `[]`, `web.url` is `""`.

## JavaScript dialogs

alert, confirm, prompt and "Leave site?" block the page until they are answered, so the
answer is set before the action that opens them:

```python
with web.dialog(accept=True, prompt_text="Ann") as d:   # accept=False = Cancel
    web.click("#prompt")
assert d.text == "Your name?"        # also d.type: alert | confirm | prompt | beforeunload
```

Leaving the block waits for the dialog (`required=False` for one that may not come). A dialog
no block expects is dismissed and listed in `web.dialogs`. Bubbles, permission prompts, Save
As, print preview and "Add extension?" are not JS dialogs: use `native`.
