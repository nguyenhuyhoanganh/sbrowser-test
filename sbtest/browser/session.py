"""BrowserSession: start/stop/restart the browser on an isolated profile.

    session = BrowserSession(cfg, name="test_x")
    session.profile.bookmarks({...})        # seed BEFORE start
    session.start()
    session.web.open("https://example.com")  # web layer (Playwright)
    session.native.hotkey("^d")             # native layer (pywinauto), Windows only
    session.restart()                       # same profile -> persistence checks
    session.stop()

We start the exe ourselves with ``--remote-debugging-port`` and Playwright attaches to it over
the DevTools protocol (``connect_over_cdp``): the browser is the real build with its real UI,
no driver binary has to match its Chromium version.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import psutil

from sbtest.browser.profile import Profile
from sbtest.browser.runtime import runtime
from sbtest.browser.version import chromium_version_from, wait_devtools_port
from sbtest.config import Config
from sbtest.utils import find_browser_pid, kill_tree, log, poll
from sbtest.web.web import Web


def merge_feature_switches(args: list[str]) -> list[str]:
    """Chromium reads only the last --disable-features / --enable-features: join the values of
    every occurrence into one switch (in place of the first), keeping the order of the rest."""
    out: list[str] = []
    for a in args:
        name, sep, value = a.partition("=")
        if sep and name in ("--disable-features", "--enable-features"):
            first = next((i for i, x in enumerate(out) if x.startswith(name + "=")), None)
            if first is not None:
                have = out[first].split("=", 1)[1].split(",")
                out[first] = f"{name}=" + ",".join(have + [v for v in value.split(",") if v and v not in have])
                continue
        out.append(a)
    return out


class BrowserCrashed(AssertionError):
    """The browser exited with a non-zero code while closing (a product failure)."""


class BrowserSession:
    def __init__(self, cfg: Config, name: str = "", profile: Profile | None = None,
                 extra_args: list[str] | None = None, extensions: list[str | Path] | None = None,
                 prefs: dict | None = None, out_dir: Path | None = None, start_page: str = "") -> None:
        self.cfg = cfg
        self.name = name
        self.artifacts = cfg.path("paths.artifacts")
        # temporary profiles and traces go with the output they belong to
        self.out_dir = Path(out_dir) if out_dir else cfg.path("paths.results")
        self.profile = profile or Profile(self.out_dir / "profiles", name)
        self.extra_args = list(extra_args or [])
        self.extensions = [str(Path(e).resolve()) for e in (extensions or [])]
        self.extra_prefs = prefs or {}
        #: internal page name (``history``) or URL the first tab opens right after the start
        self.start_page = start_page if start_page is not None else ""
        self.browser = None            # Playwright Browser (the DevTools connection)
        self.context = None            # its default context: the profile's tabs
        self.web: Web | None = None
        #: {"chromium": "151.0.7700.1", "user_agent": ..., "product": ...} of the running build
        self.info: dict = {}
        self._trace_on = False
        self._trace_parts: list[Path] = []
        self._native = None
        self._attach_proc: subprocess.Popen | None = None
        self._prefs_seeded = False
        self.timings: dict[str, float] = {}
        self.pid: int | None = None

    # -- resolution --------------------------------------------------------------
    @property
    def exe(self) -> str:
        if not self.cfg.get("browser.exe"):
            raise RuntimeError("Browser exe not set: use --exe, SB_EXE or browser.exe in config/local.yaml")
        exe = self.cfg.path("browser.exe")  # relative paths are relative to the repo root
        if not exe.exists():
            raise FileNotFoundError(f"Browser exe not found: {exe}")
        return str(exe)

    # -- options -----------------------------------------------------------------
    def _browser_args(self) -> list[str]:
        args = list(self.cfg.get("browser.args") or [])
        if self.cfg.get("browser.headless"):
            args.append("--headless=new")
        if os.name != "nt" and os.geteuid() == 0:
            args += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]  # Linux CI containers only
        w, h = self.cfg.get("browser.window_size") or (1400, 900)
        args += [f"--window-size={w},{h}", f"--user-data-dir={self.profile.dir}"]
        proxy = self.cfg.get("network.browser_proxy")
        if proxy:
            args += [f"--proxy-server={proxy}", f"--proxy-bypass-list={self.cfg.get('network.proxy_bypass') or '<local>'}"]
        if self.extensions:
            joined = ",".join(self.extensions)
            # Chromium 137+ gates --load-extension behind this feature
            args += [f"--load-extension={joined}", f"--disable-extensions-except={joined}",
                     "--disable-features=DisableLoadExtensionCommandLineSwitch"]
        return merge_feature_switches(args + self.extra_args)

    def _seed_prefs(self) -> None:
        if self._prefs_seeded:  # restart(): keep what the test changed
            return
        self._prefs_seeded = True
        prefs = dict(self.cfg.get("browser.prefs") or {})
        prefs["download.default_directory"] = str(self.profile.downloads)
        prefs["savefile.default_directory"] = str(self.profile.downloads)
        prefs.update(self.extra_prefs)
        self.profile.prefs(prefs)

    # -- lifecycle ---------------------------------------------------------------
    @property
    def alive(self) -> bool:
        """True while the browser is started and the connection to it is open."""
        return self.web is not None and self.browser is not None and self.browser.is_connected()

    def start(self) -> "BrowserSession":
        rt = runtime()   # first call of the process starts Playwright (about a second)
        t0 = time.monotonic()
        self._seed_prefs()
        try:   # whatever fails while starting, the browser launched here must not stay on screen
            # restart(): the previous run's port file would point at a dead port
            (self.profile.dir / "DevToolsActivePort").unlink(missing_ok=True)
            self._attach_proc = subprocess.Popen([self.exe, *self._browser_args(), "--remote-debugging-port=0",
                                                  "about:blank"],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            port = wait_devtools_port(self.profile.dir)
            t_browser = time.monotonic()
            page = rt.run(self._attach(rt, port), 60, "attach to the browser")
            # where the start time goes (shown per test by run.py and in the summary)
            self.timings = {"browser": round(t_browser - t0, 1), "attach": round(time.monotonic() - t_browser, 1)}
        except Exception as e:
            blocking = self._blocking_dialogs()
            if self._attach_proc:   # a leftover window would cover the next tests (their clicks land on it)
                kill_tree(self._attach_proc.pid)
                self._attach_proc = None
            self.browser = self.context = None
            if blocking:
                raise RuntimeError(
                    f"the browser shows {', '.join(blocking)} instead of starting"
                    + (f" - its profile path is too long ({len(str(self.profile.dir))} characters: "
                       f"{self.profile.dir}); move the repo to a shorter folder such as C:\\sbtest"
                       if any("profile" in t.lower() for t in blocking) else "")) from e
            raise
        self.pid = self._attach_proc.pid
        self.web = Web(self.context, page, self.cfg, native_factory=lambda: self.native)
        self._open_start_page()
        log.info("Started browser pid=%s chromium=%s profile=%s", self.pid, self.info.get("chromium"), self.profile.dir)
        return self

    async def _attach(self, rt, port: int):
        self.browser = await rt.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=45000)
        self.context = self.browser.contexts[0]
        self.context.set_default_timeout(float(self.cfg.get("timeouts.default", 10)) * 1000)
        self.context.set_default_navigation_timeout(float(self.cfg.get("timeouts.page_load", 30)) * 1000)
        cdp = await self.browser.new_browser_cdp_session()
        # Playwright redirects downloads into its own temp folder under random names: give them
        # back to the browser (the profile's download folder, the Downloads bubble, Save As)
        await cdp.send("Browser.setDownloadBehavior", {"behavior": "default"})
        v = await cdp.send("Browser.getVersion")
        self.info = {"product": v.get("product", ""), "user_agent": v.get("userAgent", ""),
                     "chromium": chromium_version_from({"Browser": v.get("product", ""),
                                                        "User-Agent": v.get("userAgent", "")}) or ""}
        await cdp.detach()
        return self.context.pages[0] if self.context.pages else await self.context.new_page()

    # -- start page --------------------------------------------------------------
    def _start_url(self) -> str:
        page = self.start_page or self.cfg.get("browser.start_page") or ""
        return self.cfg.page_url(page) if page else ""

    def _open_start_page(self) -> None:
        """Send the first tab from about:blank to the start page without waiting for it: it
        loads while the fixtures finish. The command line cannot open chrome:// pages
        (Chromium drops them); the home page (newtab) is not used: Samsung blocks DevTools
        on it."""
        url = self._start_url()
        if not url:
            return
        if "newtab" in url:
            log.warning("start page %s skipped: DevTools is blocked on the home page", url)
            return
        try:
            self.web.run(self.web.page.goto(url, wait_until="commit"), 10)
            self.web.preloaded_url = url
        except Exception as e:  # noqa: BLE001 - the test opens the page itself then
            log.warning("start page %s not opened (%s)", url, e)

    def _blocking_dialogs(self) -> list[str]:
        """Titles of message boxes the browser shows on start ("Profile error occurred"), which
        keep it from answering DevTools. Windows only; [] when there are none."""
        pid = self._attach_proc.pid if self._attach_proc else find_browser_pid(str(self.profile.dir))
        if os.name != "nt" or not pid:
            return []
        try:
            import ctypes
            from ctypes import wintypes

            pids = {pid} | {c.pid for c in psutil.Process(pid).children(recursive=True)}
            user32, titles = ctypes.windll.user32, []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _each(hwnd, _):
                owner = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, cls, 64)
                if owner.value in pids and cls.value == "#32770" and user32.IsWindowVisible(hwnd):
                    text = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(hwnd, text, 256)
                    titles.append(f'"{text.value}"')
                return True

            user32.EnumWindows(_each, 0)
            return titles
        except Exception:  # noqa: BLE001 - only a better error message
            return []

    @property
    def native(self):
        """pywinauto wrapper of this browser's windows (None when native is disabled)."""
        if not self.cfg.native_enabled:
            return None
        if self._native is None:
            from sbtest.native.browser_ui import NativeBrowser

            pid = self.pid or poll(lambda: find_browser_pid(str(self.profile.dir)), 15, message="browser pid")
            self._native = NativeBrowser(pid, self.cfg)
        return self._native

    @property
    def downloads_dir(self) -> Path:
        return self.profile.downloads

    def stop(self, remove_profile: bool | None = None) -> None:
        if self.browser is not None:
            try:   # closes the connection only: the browser is ours to stop, below
                runtime().run(self.browser.close(), 10)
            except Exception as e:  # noqa: BLE001 - browser may already be gone
                log.debug("disconnect failed: %s", e)
        for pid in filter(None, [self._attach_proc.pid if self._attach_proc else None,
                                 find_browser_pid(str(self.profile.dir))]):
            kill_tree(pid)
        self.browser = self.context = self.web = self._native = self._attach_proc = None
        self.pid = None
        self._trace_on = False
        if remove_profile if remove_profile is not None else not self.cfg.get("browser.keep_profile"):
            self.profile.remove()

    def restart(self) -> "BrowserSession":
        """Close and reopen on the same profile (checks that data/settings persist).

        Closes through the browser itself (CDP Browser.close) so it flushes prefs and
        bookmarks to disk like a user quitting; kills it only if it has not exited after 15 s.
        Raises BrowserCrashed when it exits with a non-zero code: it crashed while closing,
        and changes it had not written yet (a bookmark edited < 2.5 s before) are lost.
        """
        exit_code = None
        tracing = self._trace_on
        if tracing:   # a trace belongs to one connection: keep this part, go on in a new one
            part = self.out_dir / "traces" / f".part{len(self._trace_parts) + 1}_{self.profile.dir.name}.zip"
            self._trace_save(part)
            self._trace_parts.append(part)
        if self.browser is not None:
            exit_code = self._close_gracefully()
        self.stop(remove_profile=False)
        if exit_code:
            raise BrowserCrashed(
                f"the browser crashed while closing (exit code {exit_code & 0xFFFFFFFF:#010x}); "
                "changes it had not saved yet are lost")
        self.start()
        if tracing:
            self.trace_begin(self.name)
        return self

    def _close_gracefully(self, timeout: float = 15) -> int | None:
        """CDP Browser.close, then wait for the browser process itself (not a process-list
        scan: a process that is exiting can drop out of it early). Returns its exit code,
        None when it is unknown or the browser had to be killed."""
        pid = self._attach_proc.pid if self._attach_proc else find_browser_pid(str(self.profile.dir))
        try:
            proc = psutil.Process(pid) if pid else None
        except psutil.NoSuchProcess:
            proc = None

        async def _close():
            cdp = await self.browser.new_browser_cdp_session()
            await cdp.send("Browser.close")

        try:
            runtime().run(_close(), 5)
        except Exception as e:  # noqa: BLE001 - connection drops while closing
            log.debug("Browser.close: %s", e)
        try:
            if self._attach_proc:
                return self._attach_proc.wait(timeout)
            return proc.wait(timeout) if proc else None
        except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
            log.warning("browser did not exit within %ss after Browser.close, killing it", timeout)
            return None

    # -- Playwright trace ----------------------------------------------------------
    def trace_begin(self, title: str = "") -> None:
        """Start recording a Playwright trace of this browser (every action with DOM snapshots
        and screenshots, console, network) - ended by ``trace_end``."""
        tracing = self.context.tracing
        try:
            if self._trace_on:
                runtime().run(tracing.start_chunk(title=title or self.name), 15)
            else:
                runtime().run(tracing.start(title=title or self.name, screenshots=True, snapshots=True), 15)
            self._trace_on = True
        except Exception as e:  # noqa: BLE001 - a trace is evidence, never a reason to fail
            log.warning("trace not started: %s", e)

    def _trace_save(self, path: Path | None) -> bool:
        try:
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
            runtime().run(self.context.tracing.stop_chunk(path=str(path) if path else None), 60)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("trace not saved: %s", e)
            return False

    def trace_end(self, path: Path | None) -> list[Path]:
        """Stop the trace: write it to ``path`` (None = throw it away). A test that restarted
        the browser has one file per browser run; returns the files written."""
        parts, self._trace_parts = self._trace_parts, []
        saved: list[Path] = []
        for i, part in enumerate(parts, 1):
            if path is not None and part.exists():
                target = path.with_name(f"{path.stem}.before-restart-{i}.zip")
                part.replace(target)
                saved.append(target)
            else:
                part.unlink(missing_ok=True)
        if self._trace_on and self.alive and self._trace_save(path) and path is not None:
            saved.append(path)
        return saved

    def __enter__(self) -> "BrowserSession":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
