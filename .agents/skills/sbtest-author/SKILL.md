---
name: sbtest-author
description: Creates and maintains the automated tests of Samsung Internet / Samsung Browser for Windows (a Chromium fork) in the sbtest repo - brings test cases from a Confluence/Jira link, pasted text, a table or an export into case docs (one Markdown file per area under tests/features) with the team's IDs, turns a case or a plain request ("test that the bookmark panel lists X", "write a test for this flow") into a stable pytest test by exploring the real build first (screenshots, DOM and UIA dumps), and repairs tests, page objects and the native UI map that broke after a Chromium merge. Holds the framework reference (Selenium web layer, pywinauto native layer, test data, page objects, conventions, feature traps). Use when test cases must be imported, a test must be written, extended or fixed, or a page object, test data or native UI handling must be added.
---

# Creating tests: cases in, stable tests out

You work on the Windows machine that has the browser. **Never guess a label, selector or
behaviour**: look at the real build, then write. This is how every test in this repo was made.
Running a build, triaging a run and the Confluence report: the `sbtest-run` skill.

Commands run in the repo root; `python` means `.venv\Scripts\python.exe` (created by
`setup.bat`). Agent shells often do not run programs from the current folder: keep the `.\`
(PowerShell, cmd) or `./` (Git Bash) in front of `setup.bat` and the venv path.

## Pick the workflow

| You have | Do |
|---|---|
| test cases as a Confluence/Jira link, pasted text, a table, an export | A, then B for each case |
| a case ID, or a plain request ("write a test for ...", "check that ...") | B |
| a test that broke ("BM-114 fails on the new build", "DL-110 broke after the merge") | C |

## Hard rules (every workflow)

- **IDs come from the team** (their own scheme, e.g. `SI-ADD-012`): use them as given, never
  invent, renumber or change one. A case without an ID -> ask the user.
- **One behaviour per case.** Before adding a case, read the feature's docs
  (`tests/features/<feature>/*.md`, overview `tests/features/TESTCASES.md`): an existing case
  that covers it is extended (or its test reused) instead of adding a near-duplicate; prefer a
  stronger existing case over a new one.
- Preconditions as data (`@pytest.mark.browser(bookmarks=..., prefs=..., extensions=[...])`,
  visited local pages); only the step under test goes through the UI.
- No `time.sleep`; wait for a condition (`web.wait_*`, page `wait_*`, `web.wait_until`,
  `native.element(..., timeout)`).
- No internet except the Web Store case. Content comes from `site` / `resources/data/`.
- Tests are independent (any order, any subset, fresh profile). Use `unique("Name")`.
- No product selectors, URLs (`internet://`), machine paths or UIA criteria in tests: they
  go to page objects (`sbtest/pages/`), `config/default.yaml`, `config/native_ui.yaml`,
  `config/local.yaml`. Allowed in tests: what our own test content defines - ids of the local
  pages (`resources/site`, e.g. `web.click("#next")`) and of the sample add-on
  (`auto_id="count"`), ui-map names (`native.click("bookmarks_button")`) and the labels a user
  reads in the case (`native.menu("Add-ons")`, `dlg.click("Remove")`).
- Never weaken an assertion to pass. The product behaves differently from the case -> do not
  bend the test: report it with the evidence paths (screenshots).
- Not automatable (real account, hardware, external apps, a prompt WebDriver cannot see) ->
  `- Automated: no (<reason>)` in the case doc and in your report.

**web or native?** Inside the page (internal pages too) -> `web` / page objects. Browser
frame, toolbar, address bar, menus, bubbles, shortcuts (Ctrl+D/H/J...), Windows dialogs,
Explorer, real mouse -> `native`, and mark the test `@pytest.mark.native`.

## A. Intake: source -> case docs

1. **Raw copy.** Confluence page / Jira issue link: read it with the
   **managing-jira-confluence** skill (child pages or attachments too when the user says so).
   Pasted text / a file: as is. Save it as Markdown, tables kept, to
   `tests/features/_inbox/<page title>.md` with the source link on the first line. `_inbox/`
   is for traceability only; tests and coverage never read it.
2. **Normalize** into `tests/features/<feature>/<area>.md`, format of `tests/features/README.md`:
   - Feature folder: `addons`, `bookmarks`, `downloads`, `history`, `general`. A new area ->
     new folder and prefix (+ the steps in `references/conventions.md`); say so in the report.
   - The source's ID in the heading, plus `- Source: <link> (section/row)`.
   - Steps: numbered, one action each, the author's wording. Expected: one bullet per
     checkable outcome. Preconditions that are data are written as data ("Bookmarks bar
     contains X").
   - `Type:` web (only page content) / native (browser toolbar, menus, bubbles, shortcuts,
     Windows dialogs) / mixed.
3. **Hand over:** `python -m sbtest.tools.coverage --feature <feature>` lists the cases with no
   test yet; automate them with B, one case at a time. Report: cases read, cases written per
   feature, ambiguities and how you resolved them, cases marked not automatable.

## B. Write a test: understand, explore, map, write, prove

Copy this checklist into your reply and tick it off:

```
- [ ] 1 request rewritten as a case (or an existing case extended)
- [ ] 2 UI explored, screenshots read, findings written down
- [ ] 3 every step mapped to the action catalogue (missing rows added)
- [ ] 4 test written (template, conventions)
- [ ] 5 green 4x in a row, whole feature green, case + overview updated
```

1. **Case.** Rewrite the request as a case before touching code (format:
   `tests/features/README.md`): ID, title, Type, Precondition, numbered Steps, Expected
   (observable facts). Put it in the file of its area: `<feature>/<area>.md` (manager page
   cases, `sanity.md`, `toolbar.md` for browser-UI flows ...).
2. **Explore the real UI** (always, before writing selectors):
   1. Machine ready? `python -m sbtest.tools.doctor` ends with READY (once per session; a new
      machine: `setup.bat`). Read `references/feature-notes.md` for the feature (known traps).
   2. An internal page: `python -m sbtest.tools.dom <page> --interactive` (lines end with a
      ready locator); with data: `--seed-bookmarks resources/data/bookmarks.yaml:seed_basic`,
      `--extension resources/extensions/sample_addon`. Native UI:
      `python -m sbtest.tools.uia_dump --find "(?i)text"`.
   3. A flow (menus, bubbles, popups, dialogs): a scratch test with `Explorer` (copy
      `templates/explore_template.py`) in `tests/_scratch/` (git-ignored), run
      `python -m pytest tests/_scratch/test_x.py -s -p no:cacheprovider`. `x.snap(label)` saves
      `artifacts/explore/<name>/NN_label.png` (browser windows + bubbles), `.dom.txt`
      (locators) and `.uia.txt`; `x.try_step(label, fn)` keeps going on errors;
      `x.find_native("(?i)text")` / `x.find_web("text")` print exact names and locators. Its
      failure evidence and chromedriver log go to `artifacts/explore/scratch-run/`
      (`test-results/` is left alone).
   4. **Open and read the screenshots** - they show what really happened: a toast instead of
      a bubble, a new tab instead of the same tab, a dialog that fades in, a label that differs.
   5. Write down what you learned (labels, where it opens, what changes): it goes into the
      page object docstring, the ui-map comment and `references/feature-notes.md`.
   6. Delete the scratch file when done.
3. **Map each step** with `references/action-catalog.md` ("the case says" -> the call).
   Missing: add a page-object method (`sbtest/pages/*.py`) or a ui-map entry
   (`config/native_ui.yaml`, `{name}` params for per-item names) from what you explored, and
   a row to the catalogue.
4. **Write** `tests/features/<feature>/test_<feature>_<area>.py` (one folder per feature, so
   a feature runs alone: `python run.py --feature bookmarks`) from
   `templates/test_template.py`, shaped as in `references/conventions.md`: each doc step =
   `with step("N. ...", expected="..."):`, the doc's Expected = assertions on state.
5. **Prove it:**
   1. `python run.py --case <ID>` until green, then 3 more runs.
   2. Once with `--screenshot-steps`: open `artifacts/test-results/steps/<test>/` (or watch
      the `--record` video in `videos/`) - each `NN-I_<kind>.jpg` frames what the step is about
      to touch; check it is the right element (a wrong one shows even when the test passes).
   3. On failure read `artifacts/test-results/failures/<test>/failure.txt`, then `screen.png` /
      `page.png`, fix, repeat.
   4. `python run.py --feature <feature>` once (nothing else broke), add
      `- Automated: tests/features/<feature>/test_x.py::test_name` under the case, run
      `python -m sbtest.tools.coverage` and refresh the overview
      (`python -m sbtest.tools.case_overview`).

The wording of a case is the author's guess at the UI: keep its meaning, use the labels the
build really shows, and say so in your report. Two complete runs of this workflow:
`references/worked-examples.md`.

## C. Repair a broken test

1. Reproduce: `python run.py --case <ID>`. Read the evidence before editing anything:
   `failure.txt`, `screen.png`, `page.png` (`references/debugging.md`: evidence files and
   typical failures).
2. Decide what changed:
   - the product's behaviour -> report it with the evidence, leave the test as it is;
   - markup or labels (same behaviour) -> dump the page (`sbtest.tools.dom`) or the browser UI
     (`sbtest.tools.uia_dump`), compare with the page object / `config/native_ui.yaml`, fix
     there - keep method names, parameters and return types (`references/page-objects.md`,
     "When a page changed");
   - a race (passes on re-run) -> find the missing wait, stale list read or shared data.
3. Record the build difference in `references/feature-notes.md` (and the page object's STATUS
   line).
4. Prove it as in B5. Many failures after a Chromium merge: `references/debugging.md`,
   "After a Chromium merge".

## Reference files

Read `references/framework-map.md` first, then only what the step needs:

| Need | Read |
|------|------|
| request / case step -> the call (pages, toolbar, bubbles, dialogs, data, asserts) | `references/action-catalog.md` |
| locators, Shadow DOM, waits, clicks/typing/drag, reading text, tabs, frames, JS dialogs | `references/web-api.md` |
| toolbar/omnibox/menus, bubbles/prompts, Save As/Open/folder, Explorer, toasts, shortcuts | `references/native-ui.md` |
| preconditions: seeded bookmarks/prefs/add-ons, local pages, files, unique values | `references/test-data.md` |
| adding or adapting a page object | `references/page-objects.md` |
| feature specifics and traps (add-ons, bookmarks, downloads, history) - before every step | `references/feature-notes.md` |
| layout, naming, markers, assertions, acting through the framework | `references/conventions.md` |
| a test fails / is flaky / a selector broke after a Chromium merge | `references/debugging.md` |
| complete examples of workflow B | `references/worked-examples.md` |

Existing tests in `tests/features/` are runnable examples of every interaction (toolbar,
bubbles, Save As / Open / folder dialogs, Explorer, add-on popups, context menus).

## Before you finish

`python -m pytest tests/framework -q` green if you touched `sbtest/` or the skills. Report:
the cases written or changed, the tests and their runs (green 4x, feature run), new page-object
methods / ui-map keys / catalogue rows, labels that differ from the case's wording, product
differences found (with evidence paths), cases marked not automatable.
