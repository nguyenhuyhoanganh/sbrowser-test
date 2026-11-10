"""Which Chromium version a (forked) browser build is based on, and its DevTools port.

The Samsung Internet product version differs from its Chromium base. The running browser
tells both over DevTools (``Browser.getVersion``): we take the ``Chrome/x.y.z.w`` token of the
product, or of the User-Agent when the product holds Samsung's own version
(``chromium_version_from``). It is shown in the report; nothing has to match it.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from sbtest.utils import log

CHROME_TOKEN = re.compile(r"(?:Chrome|Chromium|HeadlessChrome)/(\d+\.\d+\.\d+\.\d+)")


def parse_chromium_version(*texts: str) -> str | None:
    """Return the first ``Chrome/x.y.z.w`` version found in the given strings."""
    for t in texts:
        m = CHROME_TOKEN.search(t or "")
        if m:
            return m.group(1)
    return None


def major(version: str) -> int:
    return int(version.split(".")[0])


def chromium_version_from(info: dict) -> str | None:
    """Chromium version from DevTools version info (``{"Browser": product, "User-Agent": ua}``).

    The User-Agent is trusted for the Chromium major ("Chrome/157.0.0.0", UA reduction): builds
    for testers may still carry a wrong number in ``Browser`` (the product version
    "Chrome/31.0.1.21" on a Chromium 157 build). ``Browser`` only adds the full version
    ("148.0.7778.217", shown in the report) when its major agrees."""
    browser = parse_chromium_version(info.get("Browser", ""))
    ua = parse_chromium_version(info.get("User-Agent", ""))
    if browser and ua and major(browser) != major(ua):
        log.warning("DevTools Browser field says %s but the User-Agent says Chrome %s: using the "
                    "User-Agent (the Browser field holds the product version)", browser, ua)
        return ua
    return browser or ua


def wait_devtools_port(user_data_dir: Path, timeout: float = 30) -> int:
    """Chromium writes the chosen port to <user-data-dir>/DevToolsActivePort."""
    f = user_data_dir / "DevToolsActivePort"
    end = time.time() + timeout
    while time.time() < end:
        try:
            first = f.read_text(errors="ignore").splitlines()[:1] if f.exists() else []
        except OSError:   # the browser holds the file while it writes it (Windows: Permission denied)
            first = []
        if first and first[0].strip().isdigit():
            return int(first[0])
        time.sleep(0.2)
    raise TimeoutError(f"Browser did not write {f} within {timeout}s")
