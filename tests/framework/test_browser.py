"""Browser start and stop: Chromium version, profile, session, processes."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from sbtest import utils
from sbtest.browser import version
from sbtest.browser.profile import expand_dotted, MAX_PROFILE_DIR, Profile, profiles_root, SHORT_ROOT
from sbtest.browser.session import BrowserCrashed, BrowserSession, merge_feature_switches
from sbtest.browser.version import chromium_version_from, parse_chromium_version
from sbtest.config import load_config
from sbtest.web.navigation import NavigationMixin


def test_parse_version():
    ua = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/141.0.7390.37 SamsungBrowser/29.0 Safari/537.36"
    assert parse_chromium_version("SamsungInternet/29.0.1.2", ua) == "141.0.7390.37"
    assert parse_chromium_version("HeadlessChrome/120.0.1.2") == "120.0.1.2"
    assert parse_chromium_version("nothing") is None


def test_chromium_version_when_browser_field_holds_the_product_version():
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "SamsungBrowser/31.0 Chrome/{} Safari/537.36")
    # Samsung 31.0.0.55: Browser holds the full Chromium version, the UA a reduced one
    assert chromium_version_from({"Browser": "Chrome/148.0.7778.217",
                                  "User-Agent": ua.format("148.0.0.0")}) == "148.0.7778.217"
    # a Samsung 31.0.2 build on Chromium 157: Browser holds the product version
    assert chromium_version_from({"Browser": "Chrome/31.0.1.21",
                                  "User-Agent": ua.format("157.0.0.0")}) == "157.0.0.0"
    assert chromium_version_from({"Browser": "", "User-Agent": ua.format("157.0.0.0")}) == "157.0.0.0"


def test_profile_prefs_merge(tmp_path):
    p = Profile(tmp_path, "t")
    p.prefs({"download.prompt_for_download": True}).prefs({"download.default_directory": "x"})
    prefs = json.loads((p.default / "Preferences").read_text())
    assert prefs["download"] == {"prompt_for_download": True, "default_directory": "x"}
    assert (p.dir / "First Run").exists()
    assert expand_dotted({"a.b.c": 1}) == {"a": {"b": {"c": 1}}}


def test_profiles_leave_a_deep_repo_folder(tmp_path):
    short = Path("C:/sbtest/artifacts/test-results/profiles")
    assert profiles_root(short) == short                     # usual repo folders keep them
    deep = Path("C:/" + "deep/" * 30) / "artifacts" / "test-results" / "profiles"
    assert profiles_root(deep) == SHORT_ROOT                 # past the 260-character limit otherwise
    assert len(str(SHORT_ROOT)) + 38 <= MAX_PROFILE_DIR


def test_devtools_port_file_read_while_the_browser_writes_it(tmp_path, monkeypatch):
    port_file = tmp_path / "DevToolsActivePort"
    port_file.write_text("51234\n/devtools/browser/x\n")
    real, calls = Path.read_text, []

    def locked_once(self, *a, **k):   # the browser holds the file on the first read
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError(13, "Permission denied")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", locked_once)
    monkeypatch.setattr(version.time, "sleep", lambda s: None)
    assert version.wait_devtools_port(tmp_path, timeout=5) == 51234 and len(calls) == 2


def test_start_page_url_and_first_open_skips_the_reload(tmp_path):
    (tmp_path / "default.yaml").write_text(yaml.safe_dump(
        {"browser": {"start_page": "history"}, "pages": {"scheme": "chrome", "history": "history", "newtab": "newtab"}}))
    cfg = load_config(config_dir=tmp_path)
    s = BrowserSession(cfg, out_dir=tmp_path)
    assert s._start_url() == s._first_url() == "chrome://history"
    blocked = BrowserSession(cfg, out_dir=tmp_path, start_page="newtab")
    assert blocked._first_url() == ""   # DevTools is blocked on the home page: no window at start
    (tmp_path / "default.yaml").write_text(yaml.safe_dump({"browser": {"start_page": ""}}))
    assert BrowserSession(load_config(config_dir=tmp_path), out_dir=tmp_path)._first_url() == ""

    gets = []
    nav = NavigationMixin()
    nav.page = SimpleNamespace(url="chrome://history/")
    nav.has_window, nav._new_window = True, None    # the browser window opened on the start page
    nav._frames = []
    nav.page_load_timeout = 30
    nav._goto = lambda url: url
    nav.run = lambda url, *a, **k: gets.append(url)
    nav.wait_ready = lambda: None
    nav.preloaded_url = "chrome://history"
    nav.open("chrome://history")      # already there: no reload
    nav.open("chrome://history")      # later opens load as usual
    assert gets == ["chrome://history"]


def test_feature_switches_are_merged_into_one():
    args = ["--lang=en-US", "--disable-features=A", "--load-extension=x",
            "--disable-features=B,A", "--enable-features=C"]
    assert merge_feature_switches(args) == ["--lang=en-US", "--disable-features=A,B",
                                            "--load-extension=x", "--enable-features=C"]


@pytest.mark.parametrize("code, crashed", [(0, False), (3, True)])
def test_restart_reports_a_crash_while_closing(tmp_path, code, crashed):
    (tmp_path / "default.yaml").write_text("{}")
    s = BrowserSession(load_config(config_dir=tmp_path), out_dir=tmp_path)
    # stands in for the browser: exits with `code` once Browser.close was sent
    s._attach_proc = subprocess.Popen([sys.executable, "-c", f"raise SystemExit({code})"])

    async def gone():                 # the connection drops while the browser closes
        raise RuntimeError("connection closed")

    s.browser = SimpleNamespace(new_browser_cdp_session=gone, close=gone, is_connected=lambda: False)
    started = []
    s.start = lambda: started.append(1) or s
    if crashed:
        with pytest.raises(BrowserCrashed, match="crashed while closing"):
            s.restart()
    else:
        s.restart()
    assert started == ([] if crashed else [1])


def test_only_test_browsers_left_by_a_crash_are_closed(monkeypatch):
    procs = [SimpleNamespace(info={"pid": 1, "cmdline": ["sb.exe", r"--user-data-dir=C:\repo\artifacts\test-results\profiles\t_1"]}),
             SimpleNamespace(info={"pid": 2, "cmdline": ["sb.exe", r"--user-data-dir=C:\repo\artifacts\test-results\profiles\t_1",
                                            "--type=renderer"]}),                         # child: goes with pid 1
             SimpleNamespace(info={"pid": 3, "cmdline": ["sb.exe", r"--user-data-dir=C:\Users\me\AppData\Samsung\User Data"]}),
             SimpleNamespace(info={"pid": 4, "cmdline": ["sb.exe"]})]                                  # the user's own browser
    killed = []
    monkeypatch.setattr(utils.psutil, "process_iter", lambda attrs: procs)
    monkeypatch.setattr(utils, "kill_tree", killed.append)
    assert utils.kill_browsers_using([r"C:\repo\artifacts\test-results\profiles"]) == [1] and killed == [1]
