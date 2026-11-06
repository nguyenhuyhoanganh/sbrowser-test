---
name: sbtest-run
description: Runs the sbtest suite against a Samsung Internet / Samsung Browser for Windows build and reports on it - asks step by step what to test (everything, the sanity pass, features, case IDs), whether to record a video or pictures of each test, the SamsungInternet.exe path and the Confluence destination, checks the machine with setup.bat, runs the tests, triages every failure (product regression, UI changed, environment, flaky) and publishes the report as a Confluence page with the managing-jira-confluence skill. Use when asked to test or check a build (e.g. after a Chromium merge), run or re-run tests, explain failures, read a run's result, or share results ("run the tests and put the result on Confluence", /sbtest-run).
---

# Run, triage, report

Paths: `references/...` is in this skill's folder (`.agents/skills/sbtest-run/`); every
other path is relative to the repo root. Commands run in the repo root. `python` means the
repo's Python: `.\.venv\Scripts\python.exe` (PowerShell), `.venv\Scripts\python` (cmd),
`.venv/Scripts/python.exe` (Git Bash). Writing or fixing tests is the `sbtest-author` skill.

Ask in the user's language (use your agent's question tool when it has one, with the options
below) and **wait for each answer** - never guess a path, a selection or a Confluence
location. Never ask again for what the user already gave (e.g. "with video" answers the
record question). The questions of steps 1-3 can go in one message.

## Which steps

| The user wants | Steps |
|---|---|
| a build tested and the result on Confluence | 1-9 |
| a run with the result in the answer ("run history", "re-run the failures") | 1, 2, 4, 5, 6, 9 |
| the failures of the last run explained ("which are real bugs?") | 6, 9 |
| the last run's result published | 3, 7, 8, 9 |

Copy the steps you do into your reply as a checklist and tick them off:

```
- [ ] 1 scope + video/pictures   - [ ] 2 exe path    - [ ] 3 Confluence target
- [ ] 4 setup READY              - [ ] 5 tests run   - [ ] 6 result read + triaged
- [ ] 7 publish confirmed        - [ ] 8 page created + attachments uploaded
- [ ] 9 final answer sent
```

Start the tests (step 5) only when every question of your steps is answered and setup is READY.

## 1. Ask what to test

| answer | arguments |
|---|---|
| everything | `--all` |
| quick sanity pass | `--sanity` |
| some features: add-ons, bookmarks, downloads, history, general | `--feature addons,bookmarks` |
| some test cases | `--case BM-113,DL-003` |

Several features can be combined; `--feature bookmarks --sanity` runs only the sanity cases of
bookmarks. To show the user which cases exist (after step 4): `python run.py --list` (always
lists every feature).

Ask whether the desktop stays free during the run: native tests drive the real mouse and
keyboard on an unlocked, visible desktop. The user needs the machine -> add `--no-native` and
say in the answer that native tests were skipped.

Ask "Record each test?" (every answer keeps the final screenshot of each case):

| answer | arguments |
|---|---|
| video of each test (recommended) | `--record` |
| a picture before every click / typing + one per step | `--screenshot-steps` |
| no, the final screenshot is enough | (nothing) |

A video or pictures make the run about 10% longer (about 10 MB of videos / 22 MB of pictures
for a full run).

## 2. Ask for the exe

`config/local.yaml` exists and has `browser.exe` -> show that path and ask the user to confirm
it or give another. Otherwise (also when the user says "this build" without a path) ask for
the full path of the build's `SamsungInternet.exe` (the file name's case does not matter).
Put it as `--exe "<path>"` on every command below; do not edit `config/local.yaml`.

## 3. Ask where to publish

Confluence space and parent page (or a page link to put it under), or "do not publish".
Only when publishing and the run records a video or pictures (step 1), ask "Which cases get
them on the Confluence page?":

| answer | arguments for step 5 |
|---|---|
| failed cases only (recommended) | (nothing) |
| every case | `--confluence-steps all` |
| none | `--confluence-steps none` |

## 4. Setup

| shell | command |
|---|---|
| PowerShell, cmd | `.\setup.bat --exe "<path>"` |
| Git Bash | `./setup.bat --exe "<path>"` |

Run it before every run (on a fresh clone it creates `.venv`). Windows only: on another OS
stop and tell the user. The last line decides:
- **READY** (with or without WARN lines) -> go on; leave WARN lines as they are (do not close
  the user's programs) and tell the user about them in step 9.
- **NOT READY** -> each `[FAIL]` line is followed by a `fix:` line: apply it, run setup again.
  Never run the tests on NOT READY.

The "Next" commands setup prints are examples; run the selection from step 1.

## 5. Run

```
python run.py <arguments from steps 1 and 3> --reruns 1 --exe "<path>"
```

`--reruns 1` runs a failed test once more: a `[RERUN]` line (with its error under it) followed
by `[PASS]` for the same case counts as passed; in step 6 it is a flaky test (bucket 4) unless
that error says the browser crashed (bucket 1).

`--all` takes 8-10 minutes, a feature 1-3 minutes: run it in the background or with a
timeout of at least 20 minutes. The run first empties `artifacts/test-results/`: when the
previous result must be kept, copy that folder elsewhere before.

## 6. Read the result and triage

`python -m sbtest.tools.summary` prints the run's summary (the run also ends with it): verdict,
totals per feature, each failure with its failed step, error and `failure.txt` path. **Quote
these numbers; never infer them.** BUILD PASSED = no failed or error case among those run
(skipped = not run); it covers only the selection that ran.

For each failure read `failure.txt`, `page.png` and `screen.png` in its folder under
`artifacts/test-results/failures/` and put it in exactly one bucket:

1. **Product regression** - behaviour differs from the case's Expected, or the error says the
   browser crashed (`BrowserCrashed`, `invalid session id`) even when a rerun passed. Do not
   touch the test.
2. **UI changed, test outdated** - same behaviour, different markup or labels after a merge.
3. **Environment** - driver/browser mismatch, locked desktop, proxy, machine crash, another
   window in front ("keyboard input would go to <process>"). Fix it (setup's `fix:` lines,
   free the desktop) and re-run.
4. **Flaky test** - `[RERUN]` then `[PASS]` in the run's output (step 5), or passes when run
   again with no product change. A case that failed only once (run without `--reruns 1`) is
   not yet bucket 1: run it again first.

Buckets 2 and 4 need a change to a test, page object or ui map: ask the user first, then do
it with the `sbtest-author` skill (`.agents/skills/sbtest-author/SKILL.md`, workflow C). After
any fix re-run the **same arguments as step 5**, not only the failed cases: the report must
cover the whole selection.

## 7. Confirm before publishing

Show the user the page title (`confluence_title` in the summary), the destination, the
verdict and the triage table. Publish only after a yes.

## 8. Publish with the managing-jira-confluence skill

With the **managing-jira-confluence** skill create a NEW page under the destination:

- title: `title` in `artifacts/test-results/confluence/manifest.json`;
- body: `page.storage.html` (Confluence storage format); `page.md` only if the skill takes
  Markdown;
- upload every file listed in `attachments` of `manifest.json` (the files of `attachments/`)
  to that page - the body references them by file name. Upload in batches if the skill limits
  a call, and check the count;
- failures triaged -> add a "Triage" section: case id | bucket | reason.

No such skill -> stop and give the user the folder `artifacts/test-results/confluence/` to
upload by hand, with the title and the triage table (case id | bucket | reason) in the answer. A case doc edited after the run -> `python -m sbtest.tools.report` rebuilds
`report/` and `confluence/` first.

## 9. Final answer

Verdict, build (Samsung + Chromium version), selection, totals per feature, the triage table,
skipped tests and why, setup's WARN lines, the Confluence page link (if published) and the
local report `artifacts/test-results/report/index.html` (videos and step pictures are inside
it when recorded).

All `run.py` options, the run's output lines and every file of the result folder:
`references/run-and-outputs.md`.
