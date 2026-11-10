"""Evidence written when a test fails, and optional screenshots after every step."""
from __future__ import annotations

import os
import time
from pathlib import Path

from sbtest.utils import log, slug

#: seconds allowed for the page part of the failure evidence (a page blocked by a modal
#: browser UI answers nothing: each command gives up after its own timeout, the rest is skipped)
WEB_EVIDENCE_BUDGET = 30
#: seconds for one evidence command
WEB_EVIDENCE_STEP = 10


def screen_grab(path: Path, session=None, cfg=None) -> Path:
    """What the user sees: the browser's windows (frame + native bubbles/dialogs), which a
    screenshot of the tab cannot show. ``report.screen_capture: screen``, or no browser window
    to find -> every monitor."""
    from PIL import ImageGrab

    path.parent.mkdir(parents=True, exist_ok=True)
    if session is not None and (cfg is None or cfg.get("report.screen_capture", "window") == "window"):
        try:
            native = session.native
            if native is not None:
                return native.screenshot(path)
        except Exception as e:  # noqa: BLE001 - fall back to the whole screen
            log.warning("browser window capture failed (%s), capturing the screen", e)
    ImageGrab.grab(all_screens=True).save(path)
    return path


def can_grab_screen(cfg) -> bool:
    return os.name == "nt" and not cfg.get("browser.headless")


# --screenshot-steps pictures: the screen is grabbed on the test's thread (it must show the
# moment), frames are drawn and the JPEG written on one background thread (flush_pictures()).
STEP_PICTURE_WIDTH = 1600
_pool = None
_pending: list = []


def _save_later(img, marks, path: Path, first: int = 1, **where) -> None:
    global _pool
    if _pool is None:
        from concurrent.futures import ThreadPoolExecutor

        _pool = ThreadPoolExecutor(1, thread_name_prefix="sbtest-pictures")

    def job():
        try:
            draw_marks(img, marks, first=first, **where)
        except Exception as e:  # noqa: BLE001 - a picture aid never fails a test
            log.warning("step picture frames failed: %s", e)
        out = img.convert("RGB")
        if out.width > STEP_PICTURE_WIDTH:
            out = out.resize((STEP_PICTURE_WIDTH, out.height * STEP_PICTURE_WIDTH // out.width))
        path.parent.mkdir(parents=True, exist_ok=True)
        out.save(path, "JPEG", quality=85)

    _pending.append(_pool.submit(job))


def flush_pictures() -> None:
    """Wait until every step picture is written (before the report reads them)."""
    while _pending:
        try:
            _pending.pop(0).result(timeout=60)
        except Exception as e:  # noqa: BLE001
            log.warning("step picture not written: %s", e)


def _grab(session, rec: dict, need_viewport: bool) -> tuple | None:
    """(image, where) of what the user sees now: the browser windows on Windows (page, toolbar,
    bubbles, dialogs), else the tab. ``where`` places the frames (see draw_marks)."""
    from io import BytesIO

    from PIL import Image, ImageGrab

    if can_grab_screen(session.cfg) and session.native is not None:
        try:
            native = session.native
            box = native.window_rect()
            img = ImageGrab.grab(bbox=box, all_screens=True)
            viewport = None
            if need_viewport:   # a UIA lookup: once per step and window position
                cache = rec.setdefault("_viewport", {})
                if box not in cache:
                    vx, vy = native.viewport_origin()
                    cache[box] = (vx - box[0], vy - box[1])
                viewport = cache[box]
            return img, {"origin": box[:2], "viewport": viewport}
        except Exception as e:  # noqa: BLE001 - fall back to the tab picture
            log.debug("step screen grab failed: %s", e)
    img = Image.open(BytesIO(session.web.screenshot_bytes()))
    return img, {"origin": (0, 0), "viewport": (0, 0), "web_only": True}


def action_picture(session, run_dir: Path, nodeid: str, rec: dict, n: int, i: int, mark: dict) -> None:
    """Picture taken right BEFORE interaction ``i`` of step ``n``, with a red frame on its
    target (the menu or dialog is still open then) -> ``steps/<test>/NN-I_<kind>.jpg``."""
    if session is None or not session.alive:
        return
    grabbed = _grab(session, rec, need_viewport=bool(mark.get("web")))
    if grabbed is None:
        return
    path = run_dir / "steps" / slug(nodeid, 150) / f"{n:02d}-{i}_{slug(mark['kind'], 20)}.jpg"
    rec.setdefault("pictures", []).append(str(path))
    _save_later(grabbed[0], [mark], path, first=i, **grabbed[1])


def step_screenshot(session, run_dir: Path, nodeid: str, rec: dict, n: int) -> None:
    """Picture of how step ``n`` ended -> ``steps/<test>/NN_<status>_<step>.jpg`` (its
    interactions have their own pictures, see action_picture)."""
    if session is None or not session.alive:
        return
    grabbed = _grab(session, rec, need_viewport=False)
    if grabbed is None:
        return
    path = run_dir / "steps" / slug(nodeid, 150) / f"{n:02d}_{rec['status']}_{slug(rec['title'], 50)}.jpg"
    rec["screenshot"] = str(path)
    _save_later(grabbed[0], [], path, **grabbed[1])


def _font(size: int):
    from PIL import ImageFont

    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_marks(img, marks: list[dict], origin: tuple[int, int] = (0, 0),
               viewport: tuple[int, int] | None = None, web_only: bool = False, first: int = 1):
    """Draw a numbered red frame + "N kind label" tag for each mark on the PIL image ``img``.

    ``web`` marks (viewport CSS px + devicePixelRatio) are placed at ``viewport`` (the page's
    top-left corner in the picture); ``screen`` marks are shifted by ``origin`` (the screen
    point of the picture's top-left corner). Marks without a place (keyboard shortcuts) and
    marks outside the picture are listed in a strip at the top."""
    if not marks:
        return img
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    width = max(3, img.width // 500)
    font = _font(max(14, img.width // 90))
    listed: list[str] = []
    for i, m in enumerate(marks, first):
        tag = f"{i} {m['kind']}" + (f" {m['label']}" if m.get("label") else "")
        box = None
        if m.get("web") and viewport is not None:
            x, y, w, h, dpr = m["web"]
            box = (viewport[0] + x * dpr, viewport[1] + y * dpr, viewport[0] + (x + w) * dpr, viewport[1] + (y + h) * dpr)
        elif m.get("screen") and not web_only:
            l, t, r, b = m["screen"]
            box = (l - origin[0], t - origin[1], r - origin[0], b - origin[1])
        inside = box is not None and box[2] > 0 and box[3] > 0 and box[0] < img.width and box[1] < img.height
        if not inside:
            if not (web_only and m.get("screen")):   # browser-UI marks belong to the screen picture
                listed.append(tag)
            continue
        l, t, r, b = (int(v) for v in box)
        draw.rectangle((l - width, t - width, r + width, b + width), outline=(230, 0, 0), width=width)
        tw, th = draw.textbbox((0, 0), tag, font=font)[2:]
        ty = t - th - 2 * width - 4 if t - th - 2 * width - 4 >= 0 else b + width + 2   # above, else below
        draw.rectangle((l - width, ty, l - width + tw + 8, ty + th + 4), fill=(230, 0, 0))
        draw.text((l - width + 4, ty + 1), tag, fill="white", font=font)
    if listed:
        text = "   ".join(listed)
        tw, th = draw.textbbox((0, 0), text, font=font)[2:]
        draw.rectangle((0, 0, tw + 12, th + 8), fill=(30, 30, 30))
        draw.text((6, 3), text, fill="white", font=font)
    return img


def result_screenshot(session, cfg, run_dir: Path, nodeid: str) -> str:
    """Picture of how a test ENDED (pass or fail), for the per-build report: the browser
    windows on Windows (native bubbles included), else the tab. Returns the path or ""."""
    out = run_dir / "results" / f"{slug(nodeid, 150)}.png"
    try:
        if can_grab_screen(cfg):
            return str(screen_grab(out, session, cfg))
        if session is not None and session.alive:
            return str(session.web.screenshot(out))
    except Exception as e:  # noqa: BLE001 - a missing picture must not fail the test
        log.warning("result screenshot failed: %s", e)
    return ""


def collect_failure(session, cfg, run_dir: Path, res: dict) -> tuple[Path, list[str]]:
    """Write everything that helps explain a failure; returns (folder, saved file names)."""
    out = run_dir / "failures" / slug(res["nodeid"], 150)
    out.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    def _try(name, fn):
        try:
            fn()
            saved.append(name)
        except Exception as e:  # noqa: BLE001 - evidence is best effort
            log.warning("evidence %s failed: %s", name, e)

    alive = session is not None and session.alive
    # OS-level evidence first: it never depends on the page (a print preview or another
    # modal browser UI can block every command sent to the page)
    if can_grab_screen(cfg) and cfg.get("report.screenshot_on_failure", True):
        _try("screen.png", lambda: screen_grab(out / "screen.png", session, cfg))
    if alive and session.native is not None and cfg.get("report.uia_on_failure", True):
        _try("uia.txt", lambda: session.native.dump(out / "uia.txt"))

    target = None
    if alive:
        web = session.web
        target = web.last_target
        if target and target[0] == "<element>":
            try:  # an element was passed instead of a locator: describe it by its markup
                outer = web.run(target[1].evaluate("e => e.outerHTML"), WEB_EVIDENCE_STEP) or ""
                target = (" ".join(outer.split())[:160], target[1])
            except Exception:  # noqa: BLE001 - detached element / page gone
                target = ("<element passed directly, no longer on the page>", target[1])
        deadline = time.monotonic() + WEB_EVIDENCE_BUDGET
        saved_timeout, web.command_timeout = web.command_timeout, WEB_EVIDENCE_STEP

        def _web(name, fn):
            if time.monotonic() < deadline:
                _try(name, fn)

        def _write(name, text_fn):
            _web(name, lambda: (out / name).write_text(text_fn(), encoding="utf-8"))

        try:
            if cfg.get("report.highlight_on_failure", True):
                web.highlight()
            if cfg.get("report.screenshot_on_failure", True):
                _web("page.png", lambda: web.screenshot(out / "page.png"))
            if cfg.get("report.dom_on_failure", True):
                from sbtest.tools.dom import dump_dom

                _write("dom.txt", lambda: f"# URL: {web.url}\n# TITLE: {web.title}\n# TABS: {len(web.tabs)}\n"
                                          + dump_dom(web))
                # the accessibility tree: roles, names and states - the short view of the page
                _write("aria.yaml", lambda: f"# URL: {web.url}\n" + web.aria_snapshot())
        finally:
            web.command_timeout = saved_timeout
        if "page.png" not in saved and "dom.txt" not in saved:
            log.warning("page evidence missing: the page did not answer (modal browser UI?)")
            (out / "page_unresponsive.txt").write_text(
                "The page did not answer while collecting evidence: a modal browser UI (print preview, "
                "a native dialog) is probably blocking it. See screen.png / uia.txt.\n", encoding="utf-8")
            saved.append("page_unresponsive.txt")
        notes = [f"[dialog] {d['type']} {d['message']!r} -> {d['answer']}"
                 + ("" if d["expected"] else "  (not expected by the test)") for d in web.dialogs] + web.console
        if notes:   # JavaScript dialogs, console errors / warnings and uncaught page errors of the test
            (out / "console.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
            saved.append("console.txt")

    lines = [
        f"test: {res['nodeid']}",
        f"cases: {', '.join(res['cases']) or '-'}",
        f"failed step: {res['failed_step'] or '-'}",
        f"expected: {res['expected'] or '-'}",
        f"error: {res['message'] or '-'}",
        f"last element: {target[0] if target else '-'}" + ("  (NOT FOUND)" if target and target[1] is None else ""),
    ]
    if alive:
        try:
            lines.append(f"url: {session.web.url}")
        except Exception:  # noqa: BLE001 - browser gone
            pass
    (out / "failure.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    saved.insert(0, "failure.txt")
    return out, saved
