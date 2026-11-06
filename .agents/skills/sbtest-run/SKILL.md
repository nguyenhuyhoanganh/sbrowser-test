---
name: sbtest-run
description: Runs the sbtest suite against a Samsung Internet / Samsung Browser for Windows build and reports on it - asks step by step what to test (everything, the sanity pass, features, case IDs), whether to record a video or pictures of each test, the SamsungInternet.exe path and the Confluence destination, checks the machine with setup.bat, runs the tests, triages every failure (product regression, UI changed, environment, flaky) and publishes the report as a Confluence page with the managing-jira-confluence skill. Use when asked to test or check a build (e.g. after a Chromium merge), run or re-run tests, explain failures, read a run's result, or share results ("run the tests and put the result on Confluence", /sbtest-run).
---

# Run, triage, report

Ask in the user's language. Use your agent's question tool when it has one (with the options
below), else ask in plain text, and **wait for each answer** - never guess a path, a
selection or a Confluence location. Never ask again for what the user already gave (scope,
exe, destination). Writing or fixing tests: the `sbtest-author` skill.

Commands run in the repo root on the Windows machine; `python` means
`.venv\Scripts\python.exe` (created by `setup.bat` in step 4). Agent shells often do not run
programs from the current folder, so always keep the `.\` / `./`:

| shell | prepare the machine | run tests |
|---|---|---|
| PowerShell | `.\setup.bat --exe "<path>"` | `.\.venv\Scripts\python.exe run.py ...` |
| cmd | `.\setup.bat --exe "<path>"` | `.venv\Scripts\python run.py ...` |
| Git Bash | `./setup.bat --exe "<path>"` | `.venv/Scripts/python.exe run.py ...` |

`setup.bat` never waits for input when nobody can answer: without `--exe` it uses
`browser.exe` of `config/local.yaml` or the installed Samsung Browser.

Every `run.py` option, what a run prints and every file of the result folder:
`references/run-and-outputs.md`.

## Which steps

| The user wants | Steps |
|---|---|
| a build tested / checked end to end, results on Confluence | 1-9 |
| a run ("run bookmarks", "re-run the failures") without publishing | 1-2 (only what is missing), 4-6, 9 |
| failures of a finished run explained ("which are real bugs?") | 6, 9 (the result folder is already there) |
| an existing result published | 3, 7-9 |

Copy this checklist into your reply (only the steps you do) and tick it off:

```
- [ ] 1 scope + evidence chosen  - [ ] 2 exe path confirmed   - [ ] 3 Confluence target known
- [ ] 4 setup READY          - [ ] 5 tests run            - [ ] 6 result read + triaged
- [ ] 7 publish confirmed     - [ ] 8 page created + attachments uploaded
- [ ] 9 final answer sent (verdict, totals, triage, link)
```

Start the tests (step 5) only when the questions of your steps are answered and setup is
READY: a run started on a guess has to be repeated.

## 1. Ask what to test

Options (several features may be combined; `--sanity` can be added to a feature selection):

| answer | arguments |
|---|---|
| everything | `--all` |
| quick sanity pass | `--sanity` |
| some features: add-ons, bookmarks, downloads, history, general | `--feature addons,bookmarks` |
| some test cases | `--case BM-113,DL-003` |

Not sure which cases exist? `python run.py --list` prints them per feature. Also ask whether
the desktop stays free during the run: native tests drive the real mouse and keyboard and need
an unlocked, visible desktop (not a minimized RDP session); if the user needs the machine, add
`--no-native` (and say so in the report).

Then two questions about the evidence of each test (offer them as options):

a. "Record each test?" - every answer keeps the final screenshot of each case.

| answer | arguments |
|---|---|
| video of each test (recommended) | `--record` |
| a picture of every click / typing + one per step | `--screenshot-steps` |
| no, the final screenshot is enough | (nothing) |

   The video shows the browser windows, the running case step as a caption and each click /
   typing framed in red (~10 MB for a full run); the pictures show the same as stills (~22 MB).
   Either makes the run ~10% longer.

b. Only after a video or pictures: "Which cases get them on the Confluence page?"

| answer | arguments |
|---|---|
| failed cases only (recommended) | (nothing) |
| every case | `--confluence-steps all` |
| none - local report only | `--confluence-steps none` |

## 2. Ask for the exe

Show the current value first (`browser.exe` in `config/local.yaml`, if any) and ask the user
to confirm it or give the full path of `SamsungInternet.exe` of the build to test. Use it as
`--exe "<path>"` on every command below (do not edit `config/local.yaml` unless asked).

## 3. Ask where to publish

Confluence space and parent page (or a page link to put it under), or "do not publish".
Asking now lets the run finish without waiting for the user.

## 4. Prepare and check the machine

```
.\setup.bat --exe "<path>"
```

Always before a run - on a fresh clone it is what creates `.venv`. It installs the packages,
then checks the machine (keyboard, Chromium version, chromedriver for the build - downloaded
when missing -, browser start, internal pages, toolbar) and ends with READY or NOT READY.
Every `[FAIL]` line has a `fix:` line (no Python, proxy, certificates, a locked desktop...):
apply it (more: `README.md`) and run `setup.bat` again; never start the tests on NOT READY.
Report the WARN lines and what you fixed. Already READY for this exe in this session:
`python -m sbtest.tools.doctor --exe "<path>"` only re-checks. The exe is not saved: keep
`--exe` on every command (`--save` makes it the default only when the user asks for that).

## 5. Run

```
python run.py <arguments from step 1> --exe "<path>"
```

`--all` takes about 8-10 minutes (more on a slow machine), a feature 1-3 minutes: start long
runs in the background or with a timeout of at least 20 minutes - a default 2-minute tool
timeout kills the run halfway. The run first empties `artifacts/test-results/` - copy that
folder elsewhere beforehand if the previous result must be kept.

## 6. Read the result and triage

`run.py` ends with a summary; print it again any time with `python -m sbtest.tools.summary`
(`--json` for the same data as JSON). It shows the verdict, totals per feature, each failure
with its failed step, error and `failure.txt`. **Quote these numbers; never infer them.**
**BUILD PASSED** = no failed or error case among those run (skipped = not run). Say which
features were run - a `--feature bookmarks` run passes only bookmarks.

For each failure read `failure.txt`, `page.png` and `screen.png` (in
`artifacts/test-results/failures/<test>/`) and put it in exactly one bucket:

1. **Product regression** - behaviour differs from the case's Expected. Evidence: case id,
   failed step, screenshots. Do not touch the test.
2. **UI changed, test outdated** - same behaviour, different markup/labels after the merge.
   Fix the page object (`sbtest/pages/`) or `config/native_ui.yaml` (`sbtest-author` skill,
   workflow C), re-run the feature.
3. **Environment** - driver/browser mismatch, locked desktop, proxy, crash of the machine,
   another window in front ("keyboard input would go to <process>"). Fix it as the `fix:`
   lines of `setup.bat` say (or free the desktop), re-run.
4. **Flaky test** - passes on re-run with no product change (`--reruns 1` separates them):
   find the race (missing wait, stale list read, shared data) and fix it; never add sleeps.

Ask the user before changing any test, page object or ui map. If you fix something, re-run
the **same arguments as step 5** (not only the failed cases): the run replaces the whole
result folder, and the report must cover the full selection.

## 7. Confirm before publishing

Show the user: page title (`confluence_title` from the summary), destination, verdict and
the triage table. Publish only after a yes. "Do not publish" in step 3 -> skip to step 9.

## 8. Publish with the managing-jira-confluence skill

Use the **managing-jira-confluence** skill to create a NEW page under the destination:

- title: `title` in `artifacts/test-results/confluence/manifest.json`
- body: `page.storage.html` (Confluence storage format); use `page.md` only if the skill
  takes Markdown
- upload every file listed in `attachments` of `manifest.json` (= every file of `attachments/`)
  to that page - the body references them by file name: result screenshots, and when recorded
  `<case>_<test>.mp4` videos (played by the Multimedia macro) and `<case>_NN-I_<kind>.jpg`
  step pictures, in one collapsed "Expand" block per case under each table. Many files:
  upload them in batches if the skill limits a call, and check the count
- failures triaged -> add a "Triage" section: case id | bucket | reason

The skill is not available -> stop and give the user the folder
`artifacts/test-results/confluence/` to upload by hand. Edited a case doc after the run?
`python -m sbtest.tools.report` rebuilds `report/` and `confluence/` first.

## 9. Final answer

Verdict, build (Samsung + Chromium version), selection, totals per feature, the triage table,
skipped tests and why (`--no-native`, no desktop), the Confluence page link, and the local
report `artifacts/test-results/report/index.html` (videos next to each case's screenshot,
"Step pictures" under each case, when they were taken; files in `videos/` and `steps/`).
Refresh the case overview with the latest results when asked:
`python -m sbtest.tools.case_overview`.
