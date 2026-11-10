"""The web layer, evidence, video and trace against a real Chromium - no Samsung build needed.

Runs headless on any Chromium: ``SBTEST_LIVE_EXE=<chrome exe>``, else the Chromium that
``python -m playwright install chromium`` puts on the machine; skipped when there is none.
It proves the framework (Playwright attach, locators, actions, dialogs, downloads, tabs,
failure evidence, tab video, trace) - not Samsung's pages: those need the build.
"""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sbtest import steps
from sbtest.config import ROOT, load_config
from sbtest.web import Keys


def _chromium() -> str:
    exe = os.environ.get("SBTEST_LIVE_EXE", "")
    if exe:
        return exe
    try:
        from sbtest.browser.runtime import runtime

        exe = runtime().playwright.chromium.executable_path
    except Exception:  # noqa: BLE001 - Playwright not installed
        return ""
    return exe if exe and Path(exe).exists() else ""


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    exe = _chromium()
    if not exe:
        pytest.skip("no Chromium to run the live checks (SBTEST_LIVE_EXE or `python -m playwright install chromium`)")
    from sbtest.browser.session import BrowserSession
    from sbtest.server import LocalSite

    cfg = load_config({"browser.exe": exe, "browser.headless": True})
    site = LocalSite(cfg.path("paths.site"), "127.0.0.1", 0).start()
    session = BrowserSession(cfg, name="live", out_dir=tmp_path_factory.mktemp("live")).start()
    yield session, site
    session.stop()
    site.stop()


@pytest.fixture
def web(live):
    session, _ = live
    web = session.web
    for tab in web.tabs[1:]:
        web.run(tab.close())
    web.switch_tab(0)
    del web.dialogs[:]
    return web


@pytest.fixture
def site(live):
    return live[1]


def test_attach_reports_the_chromium_version(live):
    session, _ = live
    assert session.alive and session.info["chromium"].split(".")[0].isdigit()


def test_locators_pierce_shadow_roots(web, site):
    web.open(site.url("/shadow.html"))
    assert web.text("my-app >>> #hdr") == "Header text"
    assert web.count("my-card") == 2 and web.count("deepcss=#action") == 2
    assert web.texts("my-app >>> my-card >>> #label") == ["First card", "Second card"]
    card = web.find("my-app >>> my-card.item")
    web.click(web.find("deep=#action", within=card))
    assert web.attr(card, "clicked") == "yes"
    assert web.exists("aria=Card action") and web.exists('role=button[name="Card action"]')
    assert web.exists("text=Do it") and web.exists("text~=header TEXT") and not web.exists("text=Header")
    assert web.exists("//h1") and web.exists("id=app") and not web.exists("#nothing")
    web.type("my-app >>> my-card >>> #field", "typed")
    assert web.value("my-app >>> my-card >>> #field") == "typed"
    assert "Header text" in web.page_text()
    assert 'button "Card action"' in web.aria_snapshot()


def test_js_returns_values_elements_and_promises(web, site):
    web.open(site.url("/form.html"))
    assert web.js("return arguments[0] + arguments[1]", 2, 3) == 5
    assert web.js("return null") is None and web.js("return {a: [1, 'x']}") == {"a": [1, "x"]}
    h1 = web.js("return document.querySelector('h1')")
    assert web.text(h1) == "Form" and web.same_element(h1, web.find("h1"))
    inputs = web.js("return Array.from(document.querySelectorAll('input'))")
    assert len(inputs) > 2 and web.js("return arguments[0].length", inputs) == len(inputs)
    assert web.js("return new Promise(done => setTimeout(() => done('later'), 50))") == "later"


def test_typing_keys_and_form_controls(web, site):
    web.open(site.url("/inputs.html"))
    web.type("#text", "hello")
    assert web.value("#text") == "hello"
    web.press(Keys.CONTROL, "a")
    web.press("Delete")
    assert web.value("#text") == ""
    web.type_keys("abc")
    assert web.value("#text") == "abc" and web.attr(web.focused(), "id") == "text"
    web.press(Keys.CONTROL, Keys.SHIFT, "x", loc="#keys")
    assert web.text("#last-key").lower() == "ctrl+shift+x"
    web.type("#editor", "rich text")
    assert web.text("#editor") == "rich text"
    assert not web.is_enabled("#disabled") and web.is_enabled("#text")
    web.select("#multi", text="Cherry")
    assert web.value("#multi") == "c"


def test_mouse_actions(web, site):
    web.open(site.url("/mouse.html"))
    web.click("#click-me")
    assert web.text("#result") == "clicked"
    web.double_click("#dbl")
    assert web.text("#result") == "double clicked"
    web.right_click("#ctx")
    web.click("#ctx-copy")
    assert web.text("#result") == "menu: copy"
    web.hover("#hover-menu")
    web.click("#sub-item")
    assert web.text("#result") == "sub item"
    web.click("#far")                       # scrolled into view first
    assert web.text("#result") == "far clicked"


def test_drag_and_drop(web, site):
    web.open(site.url("/dragdrop.html"))
    web.drag_and_drop("#drag-html5", "#drop-html5", method="html5")
    assert web.text("#html5-result") == "dropped:html5"
    web.drag_by("#mouse-drag", 100, 40)
    assert web.text("#mouse-result").startswith("moved:")


def test_dialogs_are_answered_as_planned(web, site):
    web.open(site.url("/dialogs.html"))
    with web.dialog(accept=True, prompt_text="Ann") as d:
        web.click("#prompt")
    assert (d.type, d.text, web.text("#result")) == ("prompt", "Your name?", "prompt:Ann")
    with web.dialog(accept=False):
        web.click("#confirm")
    assert web.text("#result") == "cancelled"
    web.click("#alert")                     # not planned: dismissed at once, the page goes on
    assert web.dialogs[-1] == {"type": "alert", "message": "Hello alert", "answer": "dismiss", "expected": False}
    with pytest.raises(TimeoutError, match="JavaScript dialog"):
        with web.dialog(timeout=0.5):
            web.click("#html-dialog")       # an in-page <dialog> is not a JavaScript dialog
    web.click("#dlg-close")


def test_leave_site_dialog_can_be_refused(web, site):
    web.open(site.url("/dialogs.html"))
    web.click("#arm-beforeunload")
    with web.dialog(accept=False) as d:
        web.open(site.page("Elsewhere"), blocking=False)
    assert d.type == "beforeunload" and "dialogs.html" in web.url
    with web.dialog(accept=True):
        web.open(site.page("Elsewhere"), blocking=False)
    web.wait_title("Elsewhere")


def test_tabs_frames_and_waits(web, site):
    web.open(site.url("/popups.html"))
    first, before = web.page, web.tabs
    web.click("#blank-link")
    web.wait_new_tab(before)
    assert web.wait_title("page 2") and len(web.tabs) == 2
    web.switch_tab(title="Popups")
    assert web.page is first
    web.switch_tab(url="/pages/page2.html")
    web.close_tab(switch_to=0)
    assert web.page is first and len(web.tabs) == 1
    web.open(site.url("/frames.html"))
    with web.frame("#inner"):
        assert not web.exists("#title") and web.exists("input")
    assert web.exists("#title")
    web.open(site.url("/delayed", ms=300, text="Ready"))
    web.wait_text("#late", "Ready")
    with pytest.raises(TimeoutError, match="element visible #never"):
        web.find("#never", timeout=0.3)
    assert web.last_target == ("#never", None)


def test_downloads_stay_with_the_browser(live, web, site):
    session, _ = live
    web.open(site.url("/downloads.html"))
    web.click("#dl-txt")
    assert web.wait_file(session.downloads_dir, "sample.txt").stat().st_size == 2048
    web.open(site.download("direct.pdf", 4096, "application/pdf"))   # a URL that only downloads
    assert web.wait_file(session.downloads_dir, "direct.pdf").stat().st_size == 4096
    web.open(site.url("/upload.html"))
    web.upload("#file", __file__)
    assert web.js("return document.querySelector('#file').files[0].name") == "test_live.py"


def test_internal_pages_open_over_devtools(web):
    web.open("chrome://version")
    assert "Version" in web.title and web.page_text()


def test_restart_keeps_the_profile(live, site):
    session, _ = live
    session.web.open(site.page("Before"))
    session.restart()
    session.web.open(site.page("After"))
    assert session.web.title == "After" and session.alive


def test_failure_evidence_of_a_page(live, web, site, tmp_path):
    from sbtest.reporting import evidence

    session, _ = live
    web.open(site.url("/dialogs.html"))
    web.click("#alert")
    web.js("console.error('boom from the page')")
    web.find("#confirm")
    res = {"nodeid": "tests/x.py::test_y", "cases": ["X-1"], "failed_step": "2. Do", "expected": "done", "message": "E"}
    out, saved = evidence.collect_failure(session, session.cfg, tmp_path, res)
    assert {"failure.txt", "page.png", "dom.txt", "aria.yaml", "console.txt"} <= set(saved)
    assert "last element: #confirm" in (out / "failure.txt").read_text()
    assert 'button "Confirm"' in (out / "aria.yaml").read_text()
    notes = (out / "console.txt").read_text()
    assert "[dialog] alert 'Hello alert' -> dismiss  (not expected by the test)" in notes and "boom from the page" in notes
    assert "#confirm" in (out / "dom.txt").read_text()


def test_tab_video_follows_the_test(live, web, site, tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    from sbtest.reporting.video import TabRecorder, recorder_for

    session, _ = live
    web.open(site.url("/mouse.html"))
    recorder = recorder_for(session, tmp_path / "v.mp4")
    assert isinstance(recorder, TabRecorder)          # headless: the screen cannot be recorded
    steps.reset()
    steps.set_listener(lambda rec, n: None, on_mark=lambda rec, n, i, m: recorder.mark(m))
    try:
        recorder.start()
        with steps.step("1. Click and open another tab"):
            web.click("#click-me")
            web.new_tab(site.url("/form.html"))
            web.type("input", "in the second tab")
            web.wait_until(lambda: recorder._page is web.page, 5, "recorder on the new tab")
    finally:
        steps.set_listener(None)
        path = recorder.stop()
    assert path and path.stat().st_size > 2000 and recorder.frames >= 3
    assert [m["kind"] for _, m in recorder.marks] == ["click", "type"] and recorder.marks[0][1]["screen"]


def test_trace_of_a_test(live, web, site, tmp_path):
    session, _ = live
    session.trace_begin("a test")
    web.open(site.url("/form.html"))
    web.click("button")
    assert session.trace_end(None) == []              # a passed test: thrown away
    session.trace_begin("another test")
    web.open(site.url("/mouse.html"))
    saved = session.trace_end(tmp_path / "t.zip")
    assert saved == [tmp_path / "t.zip"] and any(n.endswith(".trace") for n in zipfile.ZipFile(saved[0]).namelist())


def test_a_run_with_video_trace_and_failure(live, tmp_path):
    """run the plugin end to end on a scratch product test: results, evidence, video, trace."""
    session, _ = live
    test = tmp_path / "test_scratch.py"
    test.write_text(
        "from sbtest.steps import step\n"
        "def test_fails(web, site):\n"
        "    with step('1. Open the form', expected='the form shows'):\n"
        "        web.open(site.url('/form.html'))\n"
        "        web.click('button')\n"
        "    with step('2. Look for what is not there', expected='found'):\n"
        "        web.find('#missing', timeout=0.5)\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    env = {**os.environ, "SB_EXE": session.exe, "SB_HEADLESS": "1", "SB_NO_EXPORT": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test), "-q", "-p", "no:cacheprovider", f"--rootdir={ROOT}",
         "-c", str(ROOT / "pytest.ini"), "--run-dir", str(run_dir), "--record", "--pw-trace", "--screenshot-steps"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    failure = next((run_dir / "failures").iterdir())
    text = (failure / "failure.txt").read_text()
    assert "failed step: 2. Look for what is not there" in text and "last element: #missing  (NOT FOUND)" in text
    assert "trace: " in text
    assert {"page.png", "dom.txt", "aria.yaml"} <= {p.name for p in failure.iterdir()}
    assert list((run_dir / "videos").glob("*.mp4")) and list((run_dir / "traces").glob("*.zip"))
    assert len(list((run_dir / "steps").rglob("*.jpg"))) >= 3
