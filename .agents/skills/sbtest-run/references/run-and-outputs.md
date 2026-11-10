# run.py options, run output, result folder

## Contents

- More run.py options
- Lines a run prints
- Result folder
- Other tools

## More run.py options

The options of SKILL.md steps 1-3 are not repeated here.

```
python run.py --feature bookmarks --native   # only tests that use the browser UI and Windows
python run.py --all --trace                  # a Playwright trace of each failed test
python run.py --case <ID> --repeat 4         # 4 runs in a row; stops at the first failing run
python run.py --list                         # the cases per feature, their Type, automated or not
python run.py --case <ID> --raw              # pytest's own output (traceback, logs)
python run.py --exe "<path>" ...             # another build than the saved one
```

## Lines a run prints

One line per test, grouped by feature: `[PASS]`, `[FAIL]`, `[ERR ]`, `[SKIP]` or `[RERUN]`,
case ID, title, duration, `(start Xs)` = the time spent starting the browser, progress
(`12/74`). Under a failure: `step:` (the case step that failed), `expected:`, `error:` and
`evidence:` (the path of its `failure.txt`).

## Result folder

`artifacts/test-results/` holds only the latest run. `<test folder>` = the test's node id with
`/` and `::` replaced by `_`.

| path | content |
|---|---|
| `report/index.html` | the report: verdict, build, one row per case (steps, expected, result, screenshot, video or step pictures) |
| `report/report.md` | the same report in Markdown |
| `share/manifest.json` | `title` and the list of `attachments` |
| `share/page.storage.html`, `share/page.md` | the Confluence page body (storage format, Markdown) |
| `share/attachments/` | `<case>_<test>.jpg`, the final screenshot of every test, plus the videos or step pictures of the cases `--share-media` selected |
| `failures/<test folder>/` | `failure.txt` (read it first), `screen.png` (browser windows and dialogs), `page.png` (the tab, last element outlined), `aria.yaml` (roles and names of the page), `console.txt` (JS dialogs, console errors), `dom.txt` and `uia.txt` (long: search them) |
| `results/<test folder>.png` | the final screenshot of each passed test |
| `videos/<test folder>.mp4` | `--record` |
| `steps/<test folder>/` | `--screenshot-steps` |
| `traces/<test folder>.zip` | `--trace`; open with `python -m playwright show-trace <zip>` |
| `results.json`, `junit.xml` | machine-readable results |

## Other tools

```
python -m sbtest.tools.doctor                # check the machine again (environment failures)
python -m sbtest.tools.summary --json        # the summary as JSON
```
