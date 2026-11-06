# Worked examples - how tests in this repo were made

Two real runs of workflow B (write a test), from the request to a green test.

## Contents

- A request that an existing case already covers (ADD-112)
- A sanity case given as text (GEN-002)

## A request that an existing case already covers (ADD-112)

Request: *"Write a test: open the add-on from the toolbar, its popup shows the add-on name
and a counter that increases when clicked."*

1. Case: existing `ADD-112` already covers it -> extend, don't duplicate. (If it did not
   exist: `tests/features/addons/toolbar.md`, Type native, Precondition "SB Sample Addon installed
   and pinned", Steps "click the add-on icon / click the popup button", Expected "popup with
   name + Clicked 0 / becomes Clicked 1".)
2. Explore: scratch test -> `native.click("extensions_button")`, `x.find_native("(?i)sb sample|pin")`
   showed `Button 'Pin SB Sample Addon'`; after pinning, `ToolbarActionView 'SB Sample Addon\nHas
   access to this site'`; clicking it showed `Document 'SB popup'`, `Button 'Clicked 0' auto_id=count`.
3. Map: ui map `addons_menu_pin` (title "Pin {name}"), `extension_action` (class
   ToolbarActionView, title_re "^{name}"); test: `native.click("addons_menu_pin", name=ADDON)`,
   `native.click("extension_action", name=ADDON)`, `native.click(POPUP_COUNTER, in_main=False)`
   (the popup is its own window).
4. Prove: `python run.py --case ADD-112` x4, then `--feature addons`.

## A sanity case given as text (GEN-002)

Given: *"GEN-002 General - open a link in a new tab. Precondition: a page with a link. Steps: open the
page; right-click the link, choose 'Open link in new tab'. Expected: a new tab opens with the
linked page; the first tab still shows the original page."*

1. Case: `coverage --feature general` -> not covered yet; ID GEN-002 as given. Written to
   `tests/features/general/general.md` with a local page as the precondition ("Static page 1",
   link "Next" to "Static page 2"), Type native (the right-click menu is browser UI).
2. Explore: scratch test, right-click `#next` with the real mouse, print `native.menu_items()`
   -> Samsung's label is **"Open in new tab"** (the case used Chrome's "Open link in new tab");
   the tab handles showed the new tab opens in the BACKGROUND. Both went into feature-notes.
3. Map: catalogue "right-click on a page" -> `native.context_menu_web(web, "#next", "Open in new tab")`,
   "new tab expected" -> `before = web.tabs` ... `web.wait_new_tab(before)`; Expected = assertions
   on the titles of both tabs. Steps titled like the doc: `step("2. Right-click the link ...")`.
4. Prove: green 4x, once with `--screenshot-steps` (the frame sat on "Open in new tab"),
   `--feature general` green, `- Automated:` added, overview regenerated.

The wording of a case is the author's guess at the UI: keep its meaning, use the labels the
build really shows, and say so in your report.
