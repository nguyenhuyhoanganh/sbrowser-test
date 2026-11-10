---
name: sbtest-run
description: Runs the sbtest suite against a Samsung Internet (Samsung Browser) for Windows build and reports the result. Asks for the SamsungInternet.exe path and prepares the machine, asks what to test (everything, the sanity pass, features, case IDs), whether to record videos or pictures and where the result goes, runs the tests, sorts every failure (regression, UI changed, environment, flaky) and delivers the local HTML report, a zip file, a new Confluence page or a Jira issue description. Use when asked to test or check a build, run or re-run tests, explain the failures of a run, or share a run's result. Writing or fixing tests is the sbtest-author skill.
---

# Running sbtest on a build

Paths are relative to the repo root; `references/` is in `.agents/skills/sbtest-run/`. Run
every command in the repo root. Where this skill writes `python`, type
`.venv/Scripts/python.exe` (a bare `python` is another interpreter).

**Never change a test, page object or `config/native_ui.yaml` on your own.** A test that looks
wrong or a UI that changed: report it and ask the user (step 4).

Open `references/run-and-outputs.md` for a `run.py` option not named here, the lines a run
prints, or a file of the result folder `artifacts/test-results/`.

## Which steps

| the user wants | steps |
|---|---|
| a build tested ("test this build", "put the result on Confluence") | Start, 1-7 |
| a run with the result in the answer ("re-run the failures") | Start, 1, 3, 4, 7 |
| the failures of the last run explained | 4, 7 |
| the last run's result shared | 2, 5, 6, 7 |

Copy the steps you do into your reply as a checklist and tick them off:

```
- [ ] Start: exe confirmed, setup READY, user told about mouse and keyboard
- [ ] 1 what to test, recording   - [ ] 2 where the result goes   - [ ] 3 tests run
- [ ] 4 failures sorted           - [ ] 5 posting confirmed       - [ ] 6 result delivered
- [ ] 7 final answer
```

Ask in the user's language and wait for each answer; the Start question and the questions of
steps 1-2 can go in one message. An answer the user already gave counts ("with video" answers
the recording question). Never guess a selection, a Confluence page or a Jira issue. Run
(step 3) only when every question is answered and setup is READY.

## Start

1. **Exe path.** The user gave one -> use it. Else `config/local.yaml` has `browser.exe` -> show
   it and ask the user to confirm it or give another. Else ask for the full path of the
   build's `SamsungInternet.exe`.
2. **Setup** (Windows only; on another OS stop and say so), in PowerShell or Git Bash:
   `./setup.bat --exe "<path>" --save`.
   It creates `.venv`, saves the exe as the default of every later command and checks the
   machine. Its verdict line (above the "Next" commands) decides: **READY** -> go on (WARN
   lines go into step 7); **NOT READY** -> apply the `fix:` line under each `[FAIL]`, run it
   again.
3. **Tests exist?** `python run.py --list`. "No test cases yet" -> stop: tests are written with
   the sbtest-author skill.
4. **Tell the user** that the tests use the real mouse and keyboard: the desktop must stay
   unlocked, and nobody may use the mouse or keyboard while tests run.

## 1. What to test

| the user wants | arguments |
|---|---|
| everything | `--all` |
| the quick sanity pass | `--sanity` |
| some features (addons, bookmarks, downloads, history, general) | `--feature addons,bookmarks` |
| some cases | `--case <ID>,<ID>` |
| the basics for a Jira ticket | `--feature <the ticket's feature> --sanity` (the feature from the issue or the user's words; unclear -> ask); say which feature you took |

They combine: `--feature bookmarks --sanity`. The user cannot leave the mouse and keyboard
unused during the run -> add `--no-native` (tests that use them are skipped; say so in
step 7).

Ask "Record each test?" (the final screenshot of every case is always kept):

| answer | arguments |
|---|---|
| a video of each test (recommended) | `--record` |
| a picture before every click or typing and after every step | `--screenshot-steps` |
| no | (nothing) |

## 2. Where the result goes

Ask "Where should the result go?" - several answers allowed:

| answer | ask also for |
|---|---|
| only the local report | - |
| a zip file | - |
| a new Confluence page | the space and parent page |
| a Jira issue's description | the issue key (e.g. `SBQA-123`) |

Confluence or Jira, but the agent has no tool or skill for it -> tell the user now that you
will give them the files and text to post themselves (step 6), and skip step 5.

The local report and the zip always hold every video and picture. Confluence or Jira, with
videos or pictures from step 1 -> ask which cases get them there:

| answer | arguments for step 3 |
|---|---|
| failed cases only (recommended) | (nothing) |
| every case | `--share-media all` |
| none | `--share-media none` |

## 3. Run

```
python run.py <arguments of steps 1 and 2> --reruns 1
```

A run takes about 5 s per test: run it in the background (or with a timeout of at least 20
minutes). It first deletes the content of `artifacts/test-results/`: copy that folder elsewhere when
the previous result must be kept. `--reruns 1` runs a failed test once more: `[RERUN]` (its error
under it) then `[PASS]` counts as passed in the verdict, and step 4 still sorts it.

## 4. Sort the failures

The run ends with its summary (`python -m sbtest.tools.summary` prints it again): the verdict,
totals per feature, each failure with its failed step, error and `failure.txt` path, and the
`share:` folder with its `title`. Quote these; never infer them. BUILD PASSED = no failed or error case in the selection that ran.

For each failure and each `[RERUN]`, read `failure.txt`, `page.png` and `screen.png` (then
`aria.yaml`, `console.txt`) in its folder under `artifacts/test-results/failures/` and give it
one label:

| label | when | do |
|---|---|---|
| **regression** | the behaviour differs from the case's Expected, or the browser crashed (`BrowserCrashed`, `Target crashed`) - also when the rerun passed | report it; leave the test as it is |
| **UI changed** | the flow works but markup, labels or browser UI differ from the case or the test - e.g. `Timed out ... element visible <locator>` while `page.png` / `aria.yaml` show that element: the selector in `sbtest/pages/` no longer matches | report it for the team to review; ask the user whether to update the test (then: sbtest-author skill, workflow C) |
| **environment** | locked desktop, another window in front ("keyboard input would go to <process>"), proxy | fix the machine (setup's `fix:` lines, close the window in front), run step 3 again |
| **flaky** | `[RERUN]` then `[PASS]` without a product difference | report it; ask the user whether to make it stable (sbtest-author skill, workflow C) |

After a fix, run the same command as step 3 again, not only the failed cases.

## 5. Confirm before posting

Confluence or Jira only: show the user the destination, the `title`, the verdict and the
label table (case ID | label | reason). Post only after a yes.

## 6. Deliver

A case doc changed after the run -> `python -m sbtest.tools.report` first. `share/` =
`artifacts/test-results/share/`.

- **Local report** (always): `python -m sbtest.tools.report --open`.
- **Zip**: `python -m sbtest.tools.report --zip` -> `artifacts/sbtest-report.zip`.
- **Confluence**: a NEW page under the given parent, with the Confluence/Jira skill or tool the
  agent has (e.g. managing-jira-confluence). Title: `title` of `share/manifest.json`. Body:
  `share/page.storage.html` (storage format; `share/page.md` when the tool takes Markdown),
  plus a section "Triage" with the label table when there are failures. Attach every file
  listed in `attachments` of `share/manifest.json`; check the count.
- **Jira**: append to the issue's description the block of
  `python -m sbtest.tools.summary --markdown`, then one line `Triage: <case ID> | <label> |
  <reason>` per failure (and the Confluence link when a page was made). Replace an older block
  that starts with `### sbtest result`; keep the rest. Attach the files of `share/attachments/`
  whose name starts with a failed case's ID (all files with `--share-media all`; none when
  every case passed); check the count. Never create a new issue.
- No Confluence/Jira tool -> do not post: give the user the `share/` folder and the
  `summary --markdown` block to paste.

## 7. Final answer

Verdict, build (Samsung and Chromium version), selection, totals per feature, the label table,
skipped tests and why, setup's WARN lines, where the result went (page link, issue key, zip
path) and `artifacts/test-results/report/index.html`.
