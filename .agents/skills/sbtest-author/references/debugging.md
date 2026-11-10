# Exploring, debugging, repairing

## Contents

- Exploring
- Evidence of a run
- Typical failures
- When a page or the browser UI changed (after a Chromium merge)

## Exploring

All tools use the exe saved by setup and write under `artifacts/`.

```
python -m sbtest.tools.dom <page> --aria                        # first look: the accessibility tree (roles, names, states)
python -m sbtest.tools.dom <page> --interactive                 # internal page or /local.html: DOM lines ending in "=> <locator>"
python -m sbtest.tools.dom bookmarks --seed-bookmarks resources/data/bookmarks.yaml:seed_basic
python -m sbtest.tools.dom extensions --extension resources/extensions/sample_addon
python -m sbtest.tools.dom history --exec "web.open(site.page('A'))" --exec "web.open('chrome://history')"
python -m sbtest.tools.dom bookmarks --uia artifacts/uia.txt    # DOM + the browser UI in one go
python -m sbtest.tools.uia_dump --out artifacts/uia_main.txt   # the browser UI (UIA tree)
python -m sbtest.tools.uia_dump --url /pages/page1.html --keys "^d" --find "(?i)bookmark|done"
python -m sbtest.tools.uia_dump --pid <pid>                    # a browser you opened by hand
python run.py --case <ID> --raw --keep-profile -- -x -s --log-cli-level=INFO
```

- `dom` lines end with `=>  <locator>`: prefer ids and stable tags over `:nth-of-type`
  (`references/web-api.md`, "Locators").
- `uia_dump` lines look like `Button 'Bookmarks' auto_id='view_1023' class='BookmarksButton'`:
  put stable criteria in `config/native_ui.yaml` (`references/native-ui.md`).
- A flow with several steps, menus or bubbles: a scratch test from
  `templates/explore_template.py` (SKILL.md, B2).
- `--keep-profile` leaves `artifacts/test-results/profiles/<test>_xxxx` (or
  `%LOCALAPPDATA%\sbtest\profiles\` when the repo folder is deep): open it with
  `SamsungInternet.exe --user-data-dir=<dir>` to look at the state by hand.

## Evidence of a run

Each run empties `artifacts/test-results/` first. `<test folder>` = the test's node id with
`/` and `::` turned into `_`.

| file | content |
|------|---------|
| `failures/<test folder>/failure.txt` | test, case ids, failed step, expected, error, last element used (+ NOT FOUND), url - read first |
| `failures/<test folder>/page.png` | the tab, the last element the test used outlined in red |
| `failures/<test folder>/screen.png` | the browser's windows as on screen: frame + bubbles / prompts / menus / its dialogs (`report.screen_capture: screen` for every monitor, e.g. File Explorer) |
| `failures/<test folder>/dom.txt` | URL, title, tab count + full shadow-piercing DOM with locators |
| `failures/<test folder>/uia.txt` | UIA tree of all browser windows |
| `failures/<test folder>/aria.yaml` | accessibility tree of the tab: roles, names, states - short enough to read whole |
| `failures/<test folder>/console.txt` | JS dialogs the test met (and how they were answered), console errors / warnings, uncaught page errors |
| `traces/<test folder>.zip` | `--trace`: Playwright trace of a failed test (every web action with DOM snapshot and screenshot); `python -m playwright show-trace <zip>` - its path is the last line of `failure.txt` |
| `steps/<test folder>/NN-I_<kind>.jpg` | `--screenshot-steps`: right BEFORE interaction I of step NN, its target in a numbered red frame (keys without a target in a strip at the top) |
| `steps/<test folder>/NN_<status>_<step>.jpg` | `--screenshot-steps`: how step NN ended |
| `videos/<test folder>.mp4` | `--record`: the same frames as a video, the running step as a caption |

A frame on the wrong element = a wrong locator or ui-map entry, even when the test passes.
The run prints the failed step under each `[FAIL]`; `run.py --raw` shows pytest's own output
(traceback, a `sbtest steps` section, captured logs).

## Typical failures

| Symptom | Likely cause / fix |
|---------|--------------------|
| `Timed out ... element visible <loc>` | selector changed (compare `dom.txt` with the page object), element hidden (collapsed tree, closed menu), or wrong frame / tab |
| works alone, fails in a run | shared state: `unique()` names, no order dependence, give the test a `browser()` marker (own browser) |
| an action lands on the wrong row, or reads old text | the list re-rendered and reuses its elements: re-find inside the wait, read rows in one JS call |
| a click takes 5 s and `page.png` shows something over the element | an overlay / snack bar / menu over it: wait for it to close (`web.click` falls back to a JS click after `timeouts.action`) |
| `TimeoutError: the browser did not answer within 30s` | the page is blocked by a modal browser UI (print preview, a native prompt): handle that with `native` first; `screen.png` shows it |
| `TimeoutError ... JavaScript dialog` | the action in `with web.dialog(...)` opened no alert / confirm / prompt (an in-page `si-dialog` is not one) |
| `keyboard input would go to <process> ..., not the browser` | another window was in front (Windows Widgets, a notification, someone using the machine): environment - keep the desktop free, run again |
| an internal page lists nothing (timeout waiting for a row) while `page.png` shows the rows | the page was hidden because other windows covered the browser; `config/default.yaml` keeps it rendering (`--disable-backgrounding-occluded-windows`, `--disable-features=CalculateNativeWinOcclusion`) - check that a `browser.args` list in `config/local.yaml` did not drop them |
| native dialog not found | a different title on this build -> `uia_dump --find`, fix `config/native_ui.yaml`; or the window is not in the foreground (RDP, lock screen) |
| typing into si-input does nothing | target the inner `>>> #input` |
| page objects fail right after `session.restart()` | they hold the old `web`: `pages.of(session.web)` |
| `BrowserCrashed: the browser crashed while closing (exit code 0x...)` | product crash on exit - a regression, leave the test as it is |
| `Target crashed` / `Target page, context or browser has been closed` | browser / renderer crashed: a regression (keep the evidence) or an unstable machine; run again once to tell them apart |
| the report names a wrong Chromium version | it comes from the running build (`Browser.getVersion`: the product, or the User-Agent when the product holds Samsung's own version); only shown, nothing depends on it |
| `X did not render at ... expected internet://...` | wrong `pages.scheme` / path, or the page object's ROOT no longer matches the page |
| the browser starts but `attach to the browser` times out | the fork must keep `--remote-debugging-port` and write `DevToolsActivePort` into the profile; another Samsung Browser on the same profile also blocks it |
| `the browser shows "Profile error occurred"`, then "cannot connect to chrome" | profile paths past Windows' 260-character limit: move the repo to a short folder such as `C:\sbtest` |

## When a page or the browser UI changed (after a Chromium merge)

1. `python run.py --all --reruns 1` on the new build; group the failures by page object /
   ui-map key.
2. Behaviour differs from the case -> a regression: report it, do not "fix" the test.
3. The flow still works but markup, labels or browser UI changed -> report it as a UI change
   for the team to review and ask the user; only on a yes change the code (4, 5).
4. Different markup: `dom <page>` (with the data the page needs), fix the class
   constants (`ROOT`, `ITEMS` ...) of the page object first, then methods whose flow changed
   (e.g. a confirmation that became a native prompt). Keep method names, parameters and return
   types - tests must not change (`references/page-objects.md`).
5. Different browser UI: `uia_dump`, fix `config/native_ui.yaml`.
6. Update the page object's STATUS line (`verified on Samsung Browser <version> (Chromium <n>)`)
   and `references/feature-notes.md`; run the feature again.
