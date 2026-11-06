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
python run.py --case <ID>,<ID>
python run.py --sanity                             # quick pass (with --feature: its sanity cases only)
python run.py --all --reruns 1                     # re-run failures once to separate flakes
python run.py --all --record                       # a video per test (step caption, framed clicks)
python run.py --all --screenshot-steps             # picture per interaction (framed) + per step
python run.py --all --record --share-media all     # share/ gets the video of every case, not only failed
python run.py --all --no-native                    # skip tests that drive the real mouse/keyboard
python run.py --list                               # cases and automation status per feature
python run.py --feature downloads -- -x -k pause   # raw pytest args after --
python run.py --case <ID> --raw                     # pytest's own output (tracebacks, logs) to debug
python run.py --case <ID> --keep-profile            # keep the profile folder to open it by hand
```

The build to test is `browser.exe` of `config/local.yaml` (saved by `setup.bat --save`);
`--exe "<path>"` on a command overrides it. `--share-media failed|all|none` picks which cases
get their video / step pictures in `share/attachments/` (default `failed`).

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

The folder holds the latest run only: it is emptied when the next run starts. `<test folder>`
= the test's node id with `/` and `::` turned into `_`
(e.g. `tests_features_history_test_history.py_test_search_history`).

| path | content |
|------|---------|
| `report/index.html` | **the build's sanity report**: verdict, build info, one row per case (steps, expected, result, screenshot; video and "Step pictures" when taken); the `report/` folder can be zipped and shared |
| `report/report.md` | same report in Markdown |
| `share/` | the files to share the run on Confluence or Jira: `manifest.json` (`title`, `attachments`), `page.storage.html` (Confluence page body), `page.md` (same body in Markdown), `attachments/` (flat: `<case>_<test>.jpg` screenshot of every test + `<case>_...` videos / step pictures of the cases chosen with `--share-media`) |
| `results.json` | every test: outcome, case ids, steps, failed step, error, screenshot, evidence paths, browser start times |
| `failures/<test folder>/` | `failure.txt` (read first), `page.png` (failing element outlined in red), `screen.png` (browser windows incl. native dialogs), `dom.txt`, `page.html`, `uia.txt`, `alert.txt` |
| `results/<test folder>.png` | final screenshot of every passed test (used by the report) |
| `videos/<test folder>.mp4` | `--record`: video of the test body - browser windows, the running case step at the bottom, each click / typing framed in red (also played in the report) |
| `steps/<test folder>/` | `--screenshot-steps`: `NN-I_<kind>.jpg` right before each interaction, its target framed in red; `NN_<status>_<step>.jpg` how each step ended (also in the report) |
| `report.html` | raw pytest-html report |
| `junit.xml` | JUnit result for CI |
| `logs/` | chromedriver logs (`profiles/` too with `--keep-profile`) |

## Tools that read a finished run

```
python -m sbtest.tools.summary            # the run's summary again (--json: same data as JSON)
python -m sbtest.tools.report [--open]    # rebuild report/ and share/ (e.g. after editing case docs)
python -m sbtest.tools.case_overview      # refresh tests/features/TESTCASES.md with the latest results
python -m sbtest.tools.coverage           # which case IDs are automated, missing or orphaned
```
