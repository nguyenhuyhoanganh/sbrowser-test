"""Write the files that share a run: python -m sbtest.tools.share_export artifacts/test-results

Writes <run_dir>/share/ (manifest.json, page.storage.html, page.md, attachments/): a Confluence
page body and the files to attach to a Confluence page or a Jira issue (the sbtest-run skill
uploads them). run.py does this automatically after every run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sbtest.reporting.share_export import export


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run_dir")
    p.add_argument("--share-media", choices=["failed", "all", "none"],
                   help="cases whose video / step pictures are shared (default: report.share_media)")
    args = p.parse_args(argv)
    out = export(Path(args.run_dir), args.share_media)
    print(f"Share folder: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
