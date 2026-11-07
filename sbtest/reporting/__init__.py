"""Run outputs.

    cases.py              read the case docs (tests/features/<feature>/<feature>.md)
    cleanup.py            empty an output folder before a run (latest run only)
    live.py               the readable console output of run.py
    evidence.py           failure evidence (failure.txt, page.png with the element outlined,
                          screen.png, dom.txt, page.html, uia.txt, alert.txt) + per-step screenshots
    video.py              --record: one MP4 per test
    results.py            results.json: one record per test (outcome, case ids, steps, evidence)
    report.py             results.json + case docs -> report/ (index.html, report.md)
    share_export.py       results.json -> share/: Confluence page body + files to attach
                          to a Confluence page or a Jira issue (uploaded by the agent)
"""
