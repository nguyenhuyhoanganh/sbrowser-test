# sbtest

Automated sanity tests for Samsung Internet (Samsung Browser) for Windows, a Chromium fork.
Selenium drives web content and internal pages, pywinauto drives the browser UI and Windows
dialogs. Each run produces a per-build report (HTML, Markdown) and the files to share it on
Confluence or Jira.

## Requirements

- Windows 10/11, an unlocked desktop (native tests use the real mouse and keyboard)
- Python 3.10+ (3.12+ recommended: its pip trusts the Windows certificate store)
- The Samsung Browser build to test (`SamsungInternet.exe`)
- Internet on first setup (packages, chromedriver); behind a proxy set `HTTPS_PROXY`
- A short repo folder such as `C:\sbtest` (browser profile paths are limited to 260 characters)

## Setup

```bat
.\setup.bat                                          & rem exe from config\local.yaml, asked the first time
.\setup.bat --exe "C:\build\SamsungInternet.exe"     & rem check a given build
.\setup.bat --exe "C:\build\SamsungInternet.exe" --save   & rem ...and make it the default
```

Installs the packages into `.venv`, then checks the machine: keyboard, Chromium version,
chromedriver (downloaded when missing), browser start, internal pages, toolbar. It ends with
`READY` or `NOT READY`; every `[FAIL]` line has a `fix:` line. Re-check only:
`.venv\Scripts\python -m sbtest.tools.doctor`.

## Run

```bat
.venv\Scripts\python run.py --sanity                  & rem quick pass
.venv\Scripts\python run.py --all                     & rem every test, about 8-10 minutes
.venv\Scripts\python run.py --feature bookmarks       & rem addons, bookmarks, downloads, history, general
.venv\Scripts\python run.py --case <ID>,<ID>
.venv\Scripts\python run.py --list                    & rem cases and automation status
```

Add `--exe "<path>"` when setup used it without `--save`. Other options: `--no-native` (skip tests that drive
the real UI), `--reruns 1`, `--record` (a video of every test: browser windows, the running
case step as a caption, clicks and typing framed in red), `--screenshot-steps` (the same as
pictures: one before every click / typing, plus one per step), `--raw` (pytest's own output).

While tests run: keep hands off the mouse and keyboard, keep the keyboard on English (US) with
Vietnamese input tools in English mode, and keep the screen unlocked.

## Results

`artifacts\test-results\` holds the latest run only:

- `report\index.html` - verdict BUILD PASSED / FAILED, one row per case with steps, expected,
  result and screenshot
- `share\` - the files to share the run: a Confluence page body and the files to attach to a
  Confluence page or a Jira issue (the screenshot of every test; with `--record` /
  `--screenshot-steps` also the videos / step pictures of failed cases - `--share-media all`
  for every case, `none` for none)
- `videos\<test>.mp4` - `--record` videos (also played in the report)
- `failures\<test>\` - `failure.txt`, screenshots, DOM and UI Automation dumps

Case overview with the latest results: `python -m sbtest.tools.case_overview` -> `tests\features\TESTCASES.md`.

## New Chromium merge

Run `setup.bat` with the new exe: chromedriver follows the build's Chromium version
automatically. Then `run.py --all`; a test that fails because labels or markup changed is fixed
in the page object (`sbtest\pages\`) or `config\native_ui.yaml`, not in the test.

## Layout

```
config/          settings: default.yaml, native_ui.yaml (browser UI names), local.yaml (this machine)
sbtest/          framework: browser, web, native, pages, reporting, tools
tests/features/  one folder per feature: case docs (*.md) + their tests; TESTCASES.md (generated, git-ignored)
tests/framework/ self-tests without a browser: python -m pytest tests/framework -q
resources/       test data, sample add-on, profile templates, local test site
artifacts/       output of runs and tools, downloaded chromedriver (git-ignored)
.agents/skills/  agent skills (Agent Skills format)
```

## Agents

Everything an agent needs is in the two skills of `.agents/skills/` (Agent Skills format):
`sbtest-author` (cases in, stable tests out: intake, explore the real build, write, repair)
and `sbtest-run` (guided build check: scope, run, triage, result to Confluence / Jira / a zip;
`/sbtest-run`). Both start the same way: ask for the exe path, run `setup.bat --save`, then ask
for the rest. Agents that do not load skills by themselves: tell them to read
`.agents/skills/sbtest-author/SKILL.md` or `.agents/skills/sbtest-run/SKILL.md` first.
