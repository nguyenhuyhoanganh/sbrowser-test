# Exploration tools, evidence, frequent errors

## Contents

- Exploration tools
- Evidence of a run
- Frequent errors
- Changed UI

## Exploration tools

Each tool starts the saved build with a new profile and writes under `artifacts/`.

```
python -m sbtest.tools.dom <page> --aria          # roles, names and states of the page
python -m sbtest.tools.dom <page> --interactive   # DOM lines ending in "=> <locator>"
python -m sbtest.tools.dom bookmarks --seed-bookmarks resources/data/bookmarks.yaml:seed_basic
python -m sbtest.tools.dom extensions --extension resources/extensions/sample_addon
python -m sbtest.tools.dom history --exec "web.open(site.page('A'))" --exec "web.open('chrome://history')"
python -m sbtest.tools.uia_dump --out artifacts/uia_main.txt     # the browser's own UI
python -m sbtest.tools.uia_dump --url /pages/page1.html --keys "^d" --find "(?i)bookmark|done"
```

`<page>` is a page name (`bookmarks`, `history`, `downloads`, `extensions`) or a path on the
local site (`/form.html`). `dom` opens `<page>` first, then runs each `--exec` line (Python;
available names: `web`, `session`, `site`, `native`, `Keys`; the download folder is
`session.downloads_dir`), then dumps the page that is open at the end. The snack bar is not
in the `--aria` output: read its text in an `--exec` line with
`print(Pages(web).downloads.wait_toast())` after `from sbtest.pages import Pages`.

## Evidence of a run

`artifacts/test-results/` holds only the latest run. `<test folder>` = the test's node id with
`/` and `::` replaced by `_`.

| file | content |
|---|---|
| `failures/<test folder>/failure.txt` | failed step, expected, error, last element used (NOT FOUND when missing), URL - read it first |
| `failures/<test folder>/screen.png` | the browser windows as on screen, bubbles and dialogs included |
| `failures/<test folder>/page.png` | the tab, with the last element used outlined in red |
| `failures/<test folder>/aria.yaml` | roles, names and states of the page; short enough to read completely |
| `failures/<test folder>/console.txt` | JS dialogs and console errors |
| `failures/<test folder>/dom.txt` | the full DOM with locators; search it, it is long |
| `failures/<test folder>/uia.txt` | the UIA tree of the browser; search it, it is long |
| `steps/<test folder>/NN-I_<kind>.jpg` | `--screenshot-steps`: just before interaction I of step NN, its element framed in red |
| `steps/<test folder>/NN_<status>_<step>.jpg` | `--screenshot-steps`: the state at the end of step NN |
| `videos/<test folder>.mp4` | `--record`: a video with the running step as caption |

`python run.py --case <ID> --raw` prints pytest's own output (traceback, logs).

## Frequent errors

| error | cause and fix |
|---|---|
| `Timed out ... element visible <locator>` | the selector changed (compare `dom.txt` with the page object), the element is hidden (closed menu, collapsed tree), or it is in another tab or frame |
| an action uses the wrong row or reads old text | the list changed between the read and the action: read the rows through the page object inside the wait |
| a click takes 5 s and `page.png` shows another element over the target | a snack bar, menu or overlay covers it: wait until it is gone |
| `the browser did not answer within 30s` | a browser dialog (print preview, a prompt) blocks the page: handle it with `native` first; `screen.png` shows it |
| `TimeoutError ... JavaScript dialog` | the action inside `with web.dialog(...)` opened no JS dialog (an `si-dialog` inside a page is not a JS dialog) |
| `keyboard input would go to <process>` | another window was in front of the browser: environment; run again with nobody using the machine |
| native dialog not found | its title differs on this build: `uia_dump --find`, then fix `config/native_ui.yaml` |

## Changed UI

Follow these steps only after the user agreed to update the code.

1. Many failures after a new build: `python run.py --all --reruns 1`, then group the failures
   by page object and ui-map key.
2. Changed markup: `python -m sbtest.tools.dom <page>` with the data the page needs; fix the
   page object's selectors first, then the methods whose steps changed
   (`references/page-objects.md`).
3. Changed browser UI: `python -m sbtest.tools.uia_dump`; fix `config/native_ui.yaml`
   (`references/native-ui.md`).
4. Run the feature again.
