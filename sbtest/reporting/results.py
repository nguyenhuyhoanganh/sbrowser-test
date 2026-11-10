"""results.json - the machine-readable outcome of a run (input of the report and the share export)."""
from __future__ import annotations

import datetime as dt
import json
import platform
from pathlib import Path


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def exe_version(path) -> str:
    """Product version of a Windows exe (Samsung Browser 31.0.0.55 - the build under test)."""
    try:
        import win32api

        info = win32api.GetFileVersionInfo(str(path), "\\")
        ms, ls = info["ProductVersionMS"], info["ProductVersionLS"]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:  # noqa: BLE001 - not Windows / no version resource
        return ""


class Results:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.meta: dict = {"started": now()}
        self.tests: dict[str, dict] = {}

    def record(self, nodeid: str, name: str, feature: str | None, cases: list[str], native: bool) -> dict:
        if nodeid not in self.tests:
            self.tests[nodeid] = {
                "nodeid": nodeid, "name": name, "feature": feature, "cases": cases, "native": native,
                "outcome": "passed", "duration": 0.0, "message": "", "failed_step": "", "expected": "",
                "steps": [], "evidence_dir": "", "evidence": [], "screenshot": "",
            }
        return self.tests[nodeid]

    def note_browser(self, session) -> None:
        """Browser / Playwright versions, taken once from the first session of the run."""
        if "browser_version" in self.meta:
            return
        try:
            from importlib.metadata import version

            self.meta["browser_version"] = session.info.get("chromium", "")
            self.meta["user_agent"] = session.info.get("user_agent", "")
            self.meta["playwright"] = version("playwright")
            self.meta["product_version"] = exe_version(session.exe)
        except Exception:  # noqa: BLE001 - informative only
            pass

    def write(self, cfg, exit_status: int) -> Path | None:
        if not self.tests:
            return None
        self.meta.update({"finished": now(), "exit_status": int(exit_status),
                          "exe": cfg.get("browser.exe"), "machine": platform.node(), "os": platform.platform(),
                          "run_dir": str(self.run_dir)})
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path = self.run_dir / "results.json"
        path.write_text(json.dumps({"meta": self.meta, "tests": list(self.tests.values())}, indent=2, default=str),
                        encoding="utf-8")
        return path
