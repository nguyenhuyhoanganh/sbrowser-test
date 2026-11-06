---
name: sbtest-run
description: Runs the sbtest suite against a Samsung Internet / Samsung Browser for Windows build and reports on it - first asks for the SamsungInternet.exe path and prepares the machine with setup.bat, then asks what to test (everything, the sanity pass, features, case IDs), whether to record a video or pictures of each test and where the result goes, runs the tests, sorts every failure (regression, UI changed, environment, flaky) and delivers the result - the local HTML report, a Confluence page, a comment on a Jira issue (both with the managing-jira-confluence skill) or a zip file. Use when asked to test or check a build (e.g. after a Chromium merge), run or re-run tests, explain failures, read a run's result, or share results ("run the tests and put the result on Confluence", /sbtest-run).
---

# Run, triage, report

Paths: `references/...` is in this skill's folder `.agents/skills/sbtest-run/`; every other
path is relative to the repo root. Commands run in the repo root. Writing or fixing tests is
the `sbtest-author` skill.

## Files of this skill (open one only when a step needs it)

| file | what it is for |
|---|---|
| `references/run-and-outputs.md` | every `run.py` option, what the run prints, every file of the result folder `artifacts/test-results/`, the tools that read a finished run |

## Which steps

| The user wants | Steps |
|---|---|
| a build tested ("test this build", "put the result on Confluence / Jira") | Start, 1-7 |
| a run with the result in the answer ("run history", "re-run the failures") | Start, 1, 3, 4, 7 |
| the failures of the last run explained ("which are real bugs?") | 4, 7 |
| the last run's result shared | 2, 5, 6, 7 |

Copy the steps you do into your reply as a checklist and tick them off:

```
- [ ] Start: exe path confirmed, setup READY, user told about mouse and keyboard
- [ ] 1 what to test, desktop, recording  - [ ] 2 where the result goes  - [ ] 3 tests run
- [ ] 4 failures sorted                   - [ ] 5 posting confirmed      - [ ] 6 result delivered
- [ ] 7 final answer sent
```

Run the tests (step 3) only when every question of your steps is answered and setup is
READY. Never guess a selection, a Confluence page or a Jira issue. The Start question and the
questions of steps 1-2 can go in one message; an answer the user already gave counts ("with
video" answers the recording question).

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

## 1. Ask what to test

"What should be tested?"

| answer | arguments |
|---|---|
| everything | `--all` |
| the quick sanity pass | `--sanity` |
| some features: add-ons, bookmarks, downloads, history, general | `--feature addons,bookmarks` |
| some test cases (their IDs) | `--case <ID>,<ID>` |

Features can be combined; `--feature bookmarks --sanity` runs only the sanity cases of
bookmarks. To show the user which cases exist (after setup): `python run.py --list` (it always
lists every feature).

"Can the desktop stay free during the run?" - no -> add `--no-native` (tests that use the
real mouse and keyboard are skipped; say so in the final answer).

"Record each test?" (every answer keeps the final screenshot of each case):

| answer | arguments |
|---|---|
| a video of each test (recommended) | `--record` |
| a picture before every click / typing + one per step | `--screenshot-steps` |
| no, the final screenshot is enough | (nothing) |

A video or pictures make the run about 10% longer (about 10 MB of videos / 22 MB of pictures
for a full run).

## 2. Ask where the result goes

"Where should the result go?" - several answers allowed:

| answer | then ask for |
|---|---|
| only the local report (enough when nobody else needs it) | nothing |
| a Confluence page | the space and parent page (or a page link to put it under) |
| a Jira issue | the issue key (e.g. `SBQA-123`) |
| a zip file to send | nothing |

Confluence or Jira chosen, and step 1 records a video or pictures -> also ask "Which cases
get their video / pictures on Confluence / Jira?":

| answer | arguments for step 3 |
|---|---|
| failed cases only (recommended) | (nothing) |
| every case | `--share-media all` |
| none (screenshots only) | `--share-media none` |

## 3. Run

```
python run.py <arguments from steps 1 and 2> --reruns 1
```

`--reruns 1` runs a failed test once more. A `[RERUN]` line (its error is printed under it)
followed by `[PASS]` for the same case counts as passed in the verdict; step 4 still sorts it.

`--all` takes 8-10 minutes, a feature 1-3 minutes: run it in the background or with a
timeout of at least 20 minutes. The run first empties `artifacts/test-results/`: when the
previous result must be kept, copy that folder elsewhere before.

## 4. Sort the failures

`python -m sbtest.tools.summary` prints the run's summary (the run also ends with it):
verdict, totals per feature, each failure with its failed step, error and `failure.txt` path,
the `share:` folder and its `title`. **Quote these numbers; never infer them.** BUILD PASSED =
no failed or error case among those run (skipped = not run); it covers only the selection
that ran.

For each failure, and each `[RERUN]` of step 3, read `failure.txt`, `page.png` and
`screen.png` in its folder under `artifacts/test-results/failures/` and give it exactly one
label:

| label | when | what to do |
|---|---|---|
| **regression** | the behaviour differs from the case's Expected, or the error says the browser crashed (`BrowserCrashed`, `invalid session id`) - also when the rerun passed | report it; do not touch the test |
| **UI changed** | the flow still works, but markup, labels or browser UI differ from the case or the test (e.g. after a Chromium merge) | report it like a regression - it is a change the team has to review; ask the user whether to update the test, and only on a yes do it with the `sbtest-author` skill (`.agents/skills/sbtest-author/SKILL.md`, workflow C) |
| **environment** | driver/browser mismatch, locked desktop, proxy, machine crash, another window in front ("keyboard input would go to <process>") | fix it (setup's `fix:` lines, free the desktop) and run again |
| **flaky** | `[RERUN]` then `[PASS]` with any other error, or it passes when run again with no product change | ask the user, then make it stable with the `sbtest-author` skill (workflow C) |

A case that failed once without `--reruns 1` is not yet a regression: run it again first.
After any fix run the **same command as step 3** again, not only the failed cases: the result
must cover the whole selection.

## 5. Confirm before posting

Only for Confluence or Jira: show the user the destination, the `title` from the summary, the
verdict and the label table (case ID | label | reason). Post only after a yes.

## 6. Deliver the result

A case doc edited after the run -> `python -m sbtest.tools.report` rebuilds `report/` and
`share/` first. `share/` = `artifacts/test-results/share/`. Do every destination of step 2:

- **Local report** (always): `python -m sbtest.tools.report --open` opens
  `artifacts/test-results/report/index.html` (videos and step pictures are inside it when
  recorded).
- **Zip file**:
  `python -c "import shutil; shutil.make_archive('artifacts/sbtest-report', 'zip', 'artifacts/test-results/report')"`
  -> `artifacts/sbtest-report.zip` (the whole report; it opens offline).
- **Confluence page** - a NEW page under the destination, with the
  **managing-jira-confluence** skill:
  - title: `title` in `share/manifest.json`;
  - body: `share/page.storage.html` (Confluence storage format; `share/page.md` only if the
    skill takes Markdown), with a "Triage" section appended when there are failures:
    `<h2>Triage</h2>` and a table case ID | label | reason;
  - attachments: every file listed in `attachments` of `share/manifest.json` - the body shows
    them by file name. Upload in batches if the skill limits a call; check the count.
- **Jira issue** - a comment on the issue, with the same skill:

  ```
  <title>
  Verdict: BUILD PASSED / FAILED - passed N, failed N, error N, skipped N
  Per feature: bookmarks 8/9, history 15/15, ...
  Triage: <case ID> | <label> | <reason>   (one line per failure)
  Confluence: <page link>                  (when made too)
  ```

  Attach the files of `share/attachments/` that belong to the failed cases (name starts with
  `<case ID>_`: the screenshot, and the video / step pictures when recorded); with
  `--share-media all` attach every file. Upload in batches if needed; check the count.

No managing-jira-confluence skill -> do not post: give the user the folder `share/` to upload
by hand (the page body and its attachments, or the files for the Jira issue), with the title
and the label table in the answer.

## 7. Final answer

Verdict, build (Samsung + Chromium version), selection, totals per feature, the label table,
skipped tests and why, setup's WARN lines, where the result went (Confluence page link, Jira
issue, zip path) and the local report `artifacts/test-results/report/index.html`.
