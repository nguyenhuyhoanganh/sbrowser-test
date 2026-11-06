# run.py, its output and the result folder

## Contents

- Commands
- What the run prints
- Result folder `artifacts/test-results/`
- Tools that read a finished run

## Commands

```
python run.py --all                                # every feature (tests/features)
python run.py --feature addons,bookmarks           # addons, bookmarks, downloads, history, general
python run.py --case ADD-001,BM-004
python run.py --sanity                             # quick pass (can be added to --feature)
python run.py --all --reruns 1                     # re-run failures once to separate flakes
python run.py --all --record                       # a video per test (step caption, framed clicks)
python run.py --all --screenshot-steps             # picture per interaction (framed) + per step
python run.py --all --record --confluence-steps all   # videos/pictures of every case on the page
python run.py --all --no-native                    # skip tests that drive the real mouse/keyboard
python run.py --list                               # cases and automation status per feature
python run.py --feature downloads -- -x -k pause   # raw pytest args after --
python run.py --case BM-004 --raw                  # pytest's own output (tracebacks, logs) to debug
python run.py --case BM-004 --keep-profile         # keep the profile folder to open it by hand
```

Every command takes `--exe "<path>"` (the build to test; default `browser.exe` of
`config/local.yaml`). `--confluence-steps failed|all|none` picks which cases get their video /
step pictures on the Confluence page (default `failed`).

Durations: `--all` about 8-10 minutes (more on a slow machine), a feature 1-3 minutes. The
video or the step pictures make a run about 10% longer (~10 MB of videos, ~22 MB of pictures
for a full run).

Browser reuse: each test gets a fresh browser by default. `--scope module` reuses one per
test file (much faster; the tests of a file then share state) - not for the build verdict
unless the user accepts it. A test with a `browser(...)` marker always gets its own browser.

## What the run prints

One line per test, grouped by feature: `[PASS]` / `[FAIL]` / `[ERR ]` / `[SKIP]`, case id,
case title, time, `(start Xs)` = the part of it spent starting the browser, progress
(`12/73`). Under a failure: `step:` (the case step that failed), `expected:`, `error:` (one
line) and `evidence:` (its `failure.txt`, read it next).

The run ends with the summary: verdict, totals per feature, every failure with its evidence
path, the report paths, and `browser start: <avg>s (browser, chromedriver, startup bubbles)`
- which part of the browser start is slow.

## Result folder `artifacts/test-results/`

The folder holds the latest run only: it is emptied when the next run starts. Read (or copy
elsewhere) the evidence of a failure, and the previous result if it must be kept, before
starting another run.

| path | content |
|------|---------|
| `report/index.html` | **the build's sanity report**: verdict, build info, one row per case (steps, expected, result, screenshot; video and "Step pictures" when taken); the `report/` folder can be zipped and shared |
| `report/report.md` | same report in Markdown |
| `confluence/` | the same report as a Confluence page: `manifest.json` (title, attachments), `page.storage.html`, `page.md`, `attachments/` (one screenshot per test + videos / step pictures of the cases chosen with `--confluence-steps`) |
| `results.json` | every test: outcome, case ids, steps, failed step, error, screenshot, evidence paths, browser start times |
| `failures/<test>/` | `failure.txt` (read first), `page.png` (failing element outlined in red), `screen.png` (browser windows incl. native dialogs), `dom.txt`, `page.html`, `uia.txt`, `alert.txt` |
| `results/<test>.png` | final screenshot of every passed test (used by the report) |
| `videos/<test>.mp4` | `--record`: video of the test body - browser windows, the running case step at the bottom, each click / typing framed in red (also played in the report) |
| `steps/<test>/` | `--screenshot-steps`: `NN-I_<kind>.jpg` right before each interaction, its target framed in red; `NN_<status>_<step>.jpg` how each step ended (also in the report) |
| `report.html` | raw pytest-html report |
| `junit.xml` | JUnit result for CI |
| `logs/` | chromedriver logs (`profiles/` too with `--keep-profile`) |

What each failure file holds and the typical errors behind them: the `sbtest-author` skill,
`.agents/skills/sbtest-author/references/debugging.md`.

## Tools that read a finished run

```
python -m sbtest.tools.summary            # the run's summary again (--json: same data as JSON)
python -m sbtest.tools.report [--open]    # rebuild report/ and confluence/ (e.g. after editing case docs)
python -m sbtest.tools.case_overview      # refresh tests/features/TESTCASES.md with the latest results
python -m sbtest.tools.coverage           # which case IDs are automated, missing or orphaned
```
