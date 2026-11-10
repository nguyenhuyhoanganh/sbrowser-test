# sbtest - notes for coding agents

Automated sanity tests for Samsung Internet (Samsung Browser) for Windows, a Chromium fork.
Playwright (attached over DevTools to a browser the framework starts itself) drives page
content; pywinauto drives the browser's own UI and Windows dialogs.

## Start here

| The task | Read first |
|---|---|
| import test cases, write / extend / repair a test, a page object, the native UI map | `.agents/skills/sbtest-author/SKILL.md` |
| run tests on a build, explain failures, share the result | `.agents/skills/sbtest-run/SKILL.md` |
| change the framework itself (`sbtest/`) | this file, then the module docstrings |

Both skills are workflows with hard rules (ask for the exe path, never guess a label, never
change an existing test without a yes). Follow them; this file does not repeat them.

## Where things are

```
sbtest/browser/    session.py: start the exe, attach Playwright, restart, trace
                   runtime.py: the one Playwright event loop (own thread, every call has a timeout)
sbtest/web/        Web = waits + actions + reader + navigation; locators.py: locator syntax -> Playwright selector
sbtest/native/     browser_ui.py (toolbar, menus, bubbles), dialogs.py (Save As / Open), uia.py
sbtest/pages/      page objects of the internal pages (selectors live here, never in tests)
sbtest/reporting/  evidence.py (failure folder, step pictures), video.py, report.py, share_export.py
sbtest/tools/      doctor, dom, uia_dump, explore, coverage, summary, report, case_overview
sbtest/pytest_plugin.py   options, fixtures (web, native, pages, site, session...), results
config/            default.yaml (every setting, commented), native_ui.yaml (UI names), local.yaml (this machine)
tests/features/    <feature>/<feature>.md case docs + test_<id>.py (empty on main: agents write them)
tests/framework/   self-tests of the framework
```

## Commands

```
python -m pytest tests/framework -q            # after any change under sbtest/ - must be green
python run.py --list | --sanity | --all | --feature <f> | --case <ID>     # product tests (Windows + the build)
python run.py --case <ID> --record --trace     # + video, + Playwright trace of a failure
python -m sbtest.tools.summary --json          # the last run, machine-readable
python -m sbtest.tools.dom <page> --aria       # what a page offers (roles, names); --interactive: locators
python -m sbtest.tools.doctor                  # can this machine run the tests?
```

`python` = the repo's `.venv` (made by `setup.bat`). Product tests need Windows, an unlocked
desktop and the Samsung build; on any other machine only `tests/framework` runs.
`tests/framework/test_live.py` exercises the whole web layer, failure evidence, video and
trace on a plain headless Chromium (`python -m playwright install chromium` once, or
`SBTEST_LIVE_EXE=<chrome>`); it is skipped when there is none - say so when you report.

## Reading a failed run (in this order)

1. `python -m sbtest.tools.summary` - verdict, each failure with its failed step and `failure.txt`.
2. `artifacts/test-results/failures/<test>/failure.txt` - step, expected, error, last element, url, trace path.
3. `screen.png` (what was on screen, native UI included), `page.png` (the tab, last element outlined).
4. `aria.yaml` (the page as roles and names - short), `console.txt` (JS dialogs, console errors).
5. `dom.txt` (full DOM with locators), `uia.txt` (browser UI tree) - search them, do not read them whole.

## Rules for framework changes

- Tests and page objects talk to `web.*` / `native.*` only; Playwright objects stay inside
  `sbtest/web`, `sbtest/browser`, `sbtest/reporting`. `web.page` + `web.run(...)` is the escape hatch.
- Playwright's async API runs on the runtime thread: call it through `runtime().run(coro, timeout)`
  / `web.run(coro)`, never from inside an event handler (handlers are `async` and `await`).
- No `time.sleep` for synchronisation: `poll` / `web.wait_until` with a message that says what was awaited.
- Evidence, video and trace must never fail a test: catch, log, go on.
- A page object keeps its method names, parameters and return types when its page changes.
- One place per fact: product behaviour in `references/feature-notes.md`, step -> call in
  `references/action-catalog.md`, settings in `config/default.yaml` comments. Update the one
  place; do not copy it into another file.
- Do not commit unless the user asks. Never commit `config/local.yaml` or `artifacts/`.
