---
name: sbtest-author
description: Writes and repairs the automated tests of Samsung Internet (Samsung Browser) for Windows in the sbtest repo. Turns test cases (a Confluence or Jira link, pasted text, a table, an export) or a plain request ("write a test that the bookmark panel lists X") into case docs and pytest tests, after checking the real build, and repairs tests, page objects or the browser-UI map that fail on a new build. Use when test cases must be imported, or a test, page object, test data or browser-UI entry must be written, extended or fixed. Running a build and reporting on it is the sbtest-run skill.
---

# Writing sbtest tests

Paths are relative to the repo root; `references/` and `templates/` are in
`.agents/skills/sbtest-author/`. Run every command in the repo root. Where this skill writes
`python`, type `.venv/Scripts/python.exe` (a bare `python` is another interpreter).

## Rules

- Never guess a label, selector or behaviour: check it on the real build first.
- Never change an existing test, page object or `config/native_ui.yaml` entry without the
  user's yes: report what you found and ask.
- Case IDs come from the user or the source and are used exactly as given (any scheme, e.g.
  `SI-ADD-012`). Never invent, renumber or change one; no ID -> ask.
- One behaviour per case. Read the feature's case doc `tests/features/<feature>/<feature>.md`
  first: when a case already covers the behaviour, extend it instead of adding another.
- Preconditions are prepared as data (`references/writing-tests.md`); only the steps of the
  case go through the UI.
- Never `time.sleep`: wait for a condition (`web.wait_*`, a page object's `wait_*`,
  `web.wait_until`, `native.wait_dialog`).
- No internet except the Web Store case: pages and data come from `site` and `resources/data/`.
- Every test runs in its own new browser with a new profile, in any order. Names a test
  creates use `unique("Name")`.
- No product selectors, internal URLs, machine paths or UIA criteria in a test: they belong in
  page objects (`sbtest/pages/`), `config/default.yaml`, `config/native_ui.yaml`. A test may
  use ids of our local pages (`web.click("#next")`), ui-map keys
  (`native.click("bookmarks_button")`) and labels the case names (`native.menu("Add-ons")`).
- Never weaken an assertion to make a test pass. The build behaves differently from the case
  -> keep the test as the case says and report the difference with the evidence paths.
- Not automatable (real account, hardware, another application) -> write
  `- Automated: no (<reason>)` under the case.

**web or native.** A step inside a page (internal pages included) uses `web` and page objects.
A step on the browser frame, toolbar, address bar, menus, bubbles, shortcuts (Ctrl+D/H/J),
Windows dialogs or File Explorer uses `native`. Case `Type`: `web` = only `web` steps,
`native` = only `native` steps, `mixed` = both. `Type: native` or `mixed` <->
`@pytest.mark.native` on the test; `Type: web` <-> no such marker.

## Files (open one when a step needs it)

| file | content |
|---|---|
| `references/case-format.md` | file names of case docs and tests, IDs, the format of a case |
| `references/writing-tests.md` | test shape, fixtures, markers, preconditions, local site pages, data files |
| `references/action-catalog.md` | a case step -> the call that performs it |
| `references/feature-notes.md` | how each feature of the product behaves, and known problems |
| `references/web-api.md` | `web`: locators, waits, actions, reading, tabs, JS dialogs |
| `references/native-ui.md` | `native`: ui map, shortcuts, menus, bubbles, Windows dialogs |
| `references/page-objects.md` | adding or changing a page object |
| `references/debugging.md` | exploration tools, evidence of a run, frequent errors, changed UI |
| `templates/explore_template.py` | start of a scratch exploration test |

## Start (before any workflow)

Ask in the user's language and wait for each answer; never ask again for what the user gave.

1. **Exe path.** The user gave one -> use it. Else `config/local.yaml` has `browser.exe` -> show
   it and ask the user to confirm it or give another. Else ask for the full path of the
   build's `SamsungInternet.exe`.
2. **Setup** (Windows only; on another OS stop and say so), in PowerShell or Git Bash:
   `./setup.bat --exe "<path>" --save`. It creates `.venv`, saves the exe as the default of
   all later commands and checks the machine. Its verdict line (above the "Next" commands)
   decides: **READY** -> continue (list the WARN lines in the final report); **NOT READY** ->
   apply the `fix:` line under each `[FAIL]`, run setup again.
3. **Tell the user** that the tests use the real mouse and keyboard: the desktop must stay
   unlocked, and nobody may use the mouse or keyboard while tests run.

## Choose the workflow

| the user gives | workflow | ask for, when missing |
|---|---|---|
| complete cases from a source: a Confluence/Jira link, pasted case text, a table, an export | A, then B for each case | the content (a link but no Confluence/Jira tool -> ask the user to paste it); the feature when the source does not say |
| a request without a complete case: an ID of a case already in a case doc, or "write a test for ..." | B | the case ID; for a new case also its steps, expected result and feature |
| a failing test ("<ID> fails on the new build") | C | the case ID or the test name |

## A. Import cases

1. Save the source as Markdown (tables kept) to `tests/features/_inbox/<source title>.md`
   (no title: the first case's ID and title), with its link on the first line (pasted text:
   "Pasted by the user"). Read a Confluence page
   or Jira issue with the Confluence/Jira skill or tool the agent has.
2. Write each case into its feature's case doc in the format of `references/case-format.md`
   (create the folder and the case doc when the feature has none yet).
3. Automate the cases one at a time with B.

## B. Write a test

Copy this checklist into your reply and tick it off:

```
- [ ] 1 case written in its case doc
- [ ] 2 feature notes read; UI checked on the build where a label or behaviour was unknown
- [ ] 3 every step mapped to a call
- [ ] 4 test written
- [ ] 5 4 runs passed, step pictures correct, feature run passed, case marked Automated
```

1. **Case.** Write the case into its case doc: `references/case-format.md`.
2. **Check the UI** that the case uses, on the real build:
   - Read the feature's section of `references/feature-notes.md`.
   - Every step has a row in `references/action-catalog.md`, and every label is written there
     or in feature-notes (also when the case names it differently) -> no exploration test.
     At most `python -m sbtest.tools.dom <page> --aria` with the data the page needs
     (`references/debugging.md`, "Exploration tools").
   - Otherwise (a step with no row, an unknown label, bubble or dialog): copy
     `templates/explore_template.py` to `tests/_scratch/test_explore_<topic>.py`, edit it, run
     `python -m pytest tests/_scratch/test_explore_<topic>.py -s -p no:cacheprovider`, and open
     the pictures in `artifacts/explore/<topic>/`. Check: a toast or a bubble, a new tab or the
     same tab, the exact label.
   - Write what you found out into the feature's section of `references/feature-notes.md`.
     Delete the scratch file.
3. **Map** every step to a call with `references/action-catalog.md`. No row fits -> add a
   page-object method (`references/page-objects.md`) or a ui-map entry
   (`references/native-ui.md`), then a row in the catalogue.
4. **Write** `tests/features/<feature>/test_<id>.py` as `references/writing-tests.md` shows.
   The case doc and the step titles keep the case's wording; the code uses the labels the build
   shows; the report lists each difference.
5. **Verify the test.** Each run deletes the previous content of `artifacts/test-results/`:
   read a run's evidence before the next run. `<test folder>` = the test's node id with `/`
   and `::` replaced by `_`.
   1. `python run.py --case <ID> --repeat 4` must end with "all 4 runs passed". A failing run
      stops it: read `artifacts/test-results/failures/<test folder>/failure.txt`, then
      `screen.png` and `page.png`; fix the test; run it again.
   2. `python run.py --case <ID> --screenshot-steps`, then open every `NN-I_<kind>.jpg` in
      `artifacts/test-results/steps/<test folder>/`. Each one shows, framed in red, the element
      that interaction I of step NN is about to use. A frame on a wrong element is a bug even
      when the test passes.
   3. `python run.py --feature <feature>`: every test passes.
   4. Add `- Automated: tests/features/<feature>/test_<id>.py::<test name>` under the case.
      `python -m sbtest.tools.coverage --feature <feature>` must show `OK <ID>` and no
      "Type mismatch" line; then run `python -m sbtest.tools.case_overview` (it rewrites
      `tests/features/TESTCASES.md`).

## C. Repair a test

1. `python run.py --case <ID>`; read `failure.txt`, `screen.png` and `page.png` of its folder
   under `artifacts/test-results/failures/` before changing anything.
2. Give the failure one label:
   - **regression**: the behaviour differs from the case's Expected, or the browser crashed
     (`BrowserCrashed`, `Target crashed`) -> report it with the evidence; do not change the
     test.
   - **UI changed**: the steps still work but markup, labels or browser UI differ -> report it
     and ask the user whether to update; after a yes follow
     `references/debugging.md`, "Changed UI".
   - **environment**: locked desktop, another window in front -> fix the machine
     (`python -m sbtest.tools.doctor`), not the test.
   - **flaky**: passes when run again -> find the missing wait or the list read before it
     changed.
3. Write the changed behaviour into `references/feature-notes.md`.
4. Verify the test as in B5.

## Finish

- A file under `sbtest/` changed -> `python -m pytest tests/framework -q` must pass.
- Report: cases written or changed, each test and its runs (4 runs passed, feature run), new
  page-object methods, ui-map keys and catalogue rows, labels that differ from the case,
  product differences with evidence paths, cases marked not automatable, setup's WARN lines.
- Do not commit unless the user asks.
