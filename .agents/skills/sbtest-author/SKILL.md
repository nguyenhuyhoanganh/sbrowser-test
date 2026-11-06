---
name: sbtest-author
description: Creates and maintains the automated tests of Samsung Internet / Samsung Browser for Windows (a Chromium fork) in the sbtest repo - first asks for the SamsungInternet.exe path and prepares the machine with setup.bat, then brings test cases from a Confluence/Jira link, pasted text, a table or an export into case docs (one Markdown file per area under tests/features) with the team's IDs, turns a case or a plain request ("test that the bookmark panel lists X", "write a test for this flow") into a stable pytest test by exploring the real build first (screenshots, DOM and UIA dumps), and repairs tests, page objects and the native UI map that broke after a Chromium merge. Holds the framework reference (Selenium web layer, pywinauto native layer, test data, page objects, conventions, feature traps). Use when test cases must be imported, a test must be written, extended or fixed, or a page object, test data or native UI handling must be added.
---

# Creating tests: cases in, stable tests out

Paths: `references/...` and `templates/...` are in this skill's folder
`.agents/skills/sbtest-author/`; every other path is relative to the repo root. Commands run
in the repo root.

**Never guess a label, selector or behaviour**: look at the real build, then write.
Running a whole build and reporting on it is the `sbtest-run` skill, not this one.

## Files of this skill (open one only when a step needs it)

| file | what it is for |
|---|---|
| `references/case-format.md` | where a case doc and its test file go, their names, IDs, the case format, `_inbox/` |
| `references/action-catalog.md` | a case step -> the call that does it (pages, toolbar, bubbles, dialogs, files, asserts) |
| `references/feature-notes.md` | the product's traps, per feature - the only place they are written |
| `references/writing-tests.md` | shape of a test, fixtures, markers, imports; preconditions as data (seeds, prefs, add-ons, local site, files, profiles) |
| `references/web-api.md` | `web`: locators, Shadow DOM, waits, clicks / typing / drag, tabs, frames, JS dialogs |
| `references/native-ui.md` | `native`: the ui map, toolbar, address bar, menus, bubbles, Save As / Open dialogs, Explorer, shortcuts |
| `references/page-objects.md` | adding or changing a page object (`sbtest/pages/`) |
| `references/debugging.md` | the exploring tools (`dom`, `uia_dump`), evidence of a run, typical failures, a page or UI changed after a merge |
| `templates/test_template.py` | starting point of a new test file |
| `templates/explore_template.py` | starting point of a scratch exploration test |

```
- [ ] Start: exe path confirmed, setup READY, user told about mouse and keyboard
- [ ] workflow picked, its inputs complete
```

Begin a workflow only when both are ticked. The Start question and the workflow questions
can go in one message.

## Start: exe path and setup

The same in `sbtest-author` and `sbtest-run`. Ask in the user's language (use your agent's
question tool when it has one) and **wait for each answer**; never guess a path. Never ask
again for what the user already gave.

1. **Exe path.** `config/local.yaml` has `browser.exe` -> show that path and ask the user to
   confirm it or give another. Otherwise (also when the user says "this build" without a
   path) ask for the full path of the build's `SamsungInternet.exe` (the file name's case
   does not matter).
2. **Setup** (Windows only; on another OS stop and tell the user). In the repo root:

   | shell | command |
   |---|---|
   | PowerShell, cmd | `.\setup.bat --exe "<path>" --save` |
   | Git Bash | `./setup.bat --exe "<path>" --save` |

   It creates `.venv`, installs the packages, saves the exe in `config/local.yaml` as the
   default of every later command, downloads chromedriver and checks the machine. The last
   line decides:
   - **READY** (with or without WARN lines) -> go on; leave WARN lines as they are (do not
     close the user's programs) and tell the user about them in the final answer.
   - **NOT READY** -> each `[FAIL]` line is followed by a `fix:` line: apply it, run setup
     again. Never go on with NOT READY.

   The "Next" commands setup prints are only examples. Later in the same session, after a
   change to the machine: `python -m sbtest.tools.doctor`.
3. **Tell the user** that tests drive the real mouse and keyboard: keep the Windows desktop
   unlocked and visible, hands off while a test runs.

`python` in every command means the repo's Python: `.\.venv\Scripts\python.exe`
(PowerShell), `.venv\Scripts\python` (cmd), `.venv/Scripts/python.exe` (Git Bash).

## Pick the workflow

Ask for what is missing:

| The user gives | Workflow | Ask for (only what is missing) |
|---|---|---|
| test cases as a Confluence/Jira link, pasted text, a table, an export | A, then B per case | the source (a link but no Confluence/Jira skill available -> ask the user to paste the content); the feature when the source does not say |
| a case ID, or a plain request ("write a test for ...", "check that ...") | B | the case ID (the team's - never invent one); for a new case also its steps, expected result and feature |
| a test that broke ("<ID> fails on the new build") | C | the case ID or test name; the error message if the user has one |

## Hard rules (every workflow)

- **IDs come from the team** (any scheme, e.g. `SI-ADD-012`): use them as given; never invent,
  renumber or change one. No ID -> ask the user.
- **One behaviour per case.** Before adding a case, read the feature's case docs
  (`tests/features/<feature>/*.md`). An existing case that covers the behaviour is extended,
  or its test reused, instead of adding a near-duplicate.
- Preconditions as data (`@pytest.mark.browser(bookmarks=..., prefs=..., extensions=[...])`,
  visited local pages); only the step under test goes through the UI.
- No `time.sleep`: wait for a condition (`web.wait_*`, page `wait_*`, `web.wait_until`,
  `native.element(..., timeout)`).
- No internet except the Web Store case. Pages and data come from `site` / `resources/data/`.
- Tests are independent (any order, any subset, fresh profile). Names a test creates use
  `unique("Name")`.
- Tests contain no product selectors, URLs (`internet://`), machine paths or UIA criteria:
  those go to page objects (`sbtest/pages/`), `config/default.yaml`, `config/native_ui.yaml`.
  Allowed in tests: ids of our own local pages (`resources/site`, e.g. `web.click("#next")`)
  and of the sample add-on (`auto_id="count"`), ui-map names (`native.click("bookmarks_button")`)
  and labels the user reads in the case (`native.menu("Add-ons")`, `dlg.click("Remove")`).
- Never weaken an assertion to pass. The product behaves differently from the case -> leave
  the test as the case says and report the difference with the evidence paths.
- Not automatable (real account, hardware, external apps, a prompt WebDriver cannot see) ->
  `- Automated: no (<reason>)` under the case and in your report.

**web or native?** Inside the page (internal pages too) -> `web` / page objects. Browser
frame, toolbar, address bar, menus, bubbles, shortcuts (Ctrl+D/H/J...), Windows dialogs,
Explorer, real mouse -> `native`, and mark the test `@pytest.mark.native`.

## A. Intake: source -> case docs

1. Read the source: a Confluence page / Jira issue with the **managing-jira-confluence** skill
   (child pages or attachments too when the user says so); pasted text or a file as is. Save
   it as Markdown, tables kept, to `tests/features/_inbox/<page title>.md`, the source link on
   the first line.
2. Write each case into its case doc - which file, its name and the format of a case:
   `references/case-format.md` (read it). The source's ID goes in the heading, with
   `- Source: <link> (section/row)`; steps, Expected and Precondition as that reference says.
3. `python -m sbtest.tools.coverage --feature <feature>` lists the cases without a test.
   Automate them with B, one case at a time.

## B. Write a test

```
- [ ] 1 case written (or an existing case extended)
- [ ] 2 UI explored, screenshots read
- [ ] 3 every step mapped to a call
- [ ] 4 test written
- [ ] 5 green 4 runs in a row, feature green, case + overview updated
```

1. **Case.** Write the request as a case in its case doc: ID, title, Type, Precondition,
   numbered Steps, Expected (observable facts); Priority only when the user or the source
   gives one. Which doc, its name and the format: `references/case-format.md`. Mark the test
   `@pytest.mark.sanity` only when the user or the source says the case is part of the sanity
   pass.
2. **Explore** what the case touches, on the real build (the commands use the saved exe):
   - Read the feature's section of `references/feature-notes.md` (known traps).
   - Every step has a row in `references/action-catalog.md` and every label it needs is named
     there or in feature-notes -> no scratch test: at most one look at an internal page with
     `python -m sbtest.tools.dom <page> --interactive` (with data, and the other tools:
     `references/debugging.md`, "Exploring"); the step pictures of B5b confirm the rest.
   - Otherwise (a step with no row, a label nobody wrote down, an unknown bubble or dialog) ->
     a scratch test: copy `templates/explore_template.py` to
     `tests/_scratch/test_explore_<topic>.py`, edit, run
     `python -m pytest tests/_scratch/test_explore_<topic>.py -s -p no:cacheprovider`.
     `x.snap(label)` saves `artifacts/explore/<topic>/NN_label.png` + `.dom.txt` + `.uia.txt`;
     `x.try_step(label, fn)` goes on after errors; `x.find_native("(?i)text")` /
     `x.find_web("text")` print exact names and locators.
   - **Open the screenshots and look at them**: a toast instead of a bubble, a new tab instead
     of the same tab, a label that differs from the case.
   - Record what you learned in the page object docstring, the ui-map comment and the
     feature's section of `references/feature-notes.md`. Delete the scratch test.
3. **Map** each step to a call with `references/action-catalog.md`. No row fits -> add a
   page-object method (`sbtest/pages/*.py`, `references/page-objects.md`) or a ui-map entry
   (`config/native_ui.yaml`, `references/native-ui.md`), then a row to the catalogue.
4. **Write** the test in the test file of its case doc
   (`tests/features/<feature>/test_<id>.py`, one per case: `references/case-format.md`);
   a new file starts from `templates/test_template.py`. Shape, fixtures, markers and
   preconditions as data: `references/writing-tests.md` - each case step =
   `with step("N. ...", expected="..."):`, the case's Expected = assertions on state.
5. **Prove it.** Each run empties `artifacts/test-results/` first: look at a run's evidence
   before starting the next one. `<test folder>` below = the test's node id with `/` and `::`
   turned into `_` (`tests_features_<feature>_test_<id>.py_<test name>`).
   a. `python run.py --case <ID>` 4 times in a row, all green (PowerShell:
      `1..4 | % { .\.venv\Scripts\python.exe run.py --case <ID> }`). A failure -> read
      `artifacts/test-results/failures/<test folder>/failure.txt`, then `screen.png` /
      `page.png`, fix, start counting again.
   b. `python run.py --case <ID> --screenshot-steps`, then open
      `artifacts/test-results/steps/<test folder>/`: each `NN-I_<kind>.jpg` frames the element
      a step is about to touch - it must be the right one (a wrong one shows even when green).
   c. `python run.py --feature <feature>`: all green.
   d. Under the case add `- Automated: tests/features/<feature>/test_<id>.py::<test name>`, then
      run `python -m sbtest.tools.coverage --feature <feature>` (the case shows OK) and
      `python -m sbtest.tools.case_overview`.

The case's wording is the author's guess at the UI: keep its meaning, use the labels the
build really shows, and say so in your report.

## C. Repair a broken test

1. `python run.py --case <ID>`; read `failure.txt`, `screen.png`, `page.png` before editing
   anything (what each evidence file holds and typical errors: `references/debugging.md`).
2. Give it one label (the same labels as the `sbtest-run` skill):
   - **regression** - the behaviour differs from the case's Expected, or the browser crashed
     (`BrowserCrashed`, `invalid session id`) -> report it with the evidence; leave the test
     as it is;
   - **UI changed** - the flow still works, different markup, labels or browser UI -> report
     it as a change the team has to review and ask the user whether to update the test; on a
     yes dump the page
     (`python -m sbtest.tools.dom <page>`) or the browser UI (`python -m sbtest.tools.uia_dump`),
     fix the page object or `config/native_ui.yaml`; keep method names, parameters and return
     types (`references/debugging.md`, "When a page or the browser UI changed");
   - **environment** - locked desktop, another window in front, driver mismatch -> fix the
     machine (`python -m sbtest.tools.doctor`), not the test;
   - **flaky** - passes when run again -> a race: find the missing wait, stale list read or
     shared data.
3. Record the build difference in `references/feature-notes.md` and in the page object's
   STATUS line.
4. Prove it as in B5. Many tests broken after a Chromium merge: `references/debugging.md`,
   "When a page or the browser UI changed".

## Before you finish

Changed any file under `sbtest/` -> `python -m pytest tests/framework -q` must be green.
Report to the user: cases written or changed, the test and its runs (4x green, feature run), new
page-object methods / ui-map keys / catalogue rows, labels that differ from the case's
wording, product differences (with evidence paths), cases marked not automatable. Do not
commit unless the user asks.
