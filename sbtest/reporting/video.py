"""``--record``: one MP4 per test instead of a picture per step.

A background thread takes a frame a few times per second, draws the running case step at the
bottom and a red frame on each interaction for a moment (the same marks as the step pictures,
``sbtest.steps.mark``), and pipes the frames to ffmpeg (``imageio-ffmpeg``) which writes H.264 -
playable in the HTML report and in the share folder. Recording never fails a test.

Two sources of frames (``recorder_for`` picks one):

- ``ScreenRecorder`` - a Windows desktop: the browser's windows as they are on screen (page,
  toolbar, bubbles, menus, its dialogs). The one that shows native steps.
- ``TabRecorder`` - anywhere else (headless, no desktop to grab): the current tab only, sent
  by the browser itself over DevTools (``Page.startScreencast``); it follows the test from tab
  to tab. Browser UI is not in the picture: native interactions are listed as text.
"""
from __future__ import annotations

import base64
import threading
import time
from io import BytesIO
from pathlib import Path

from sbtest import steps
from sbtest.utils import log

FPS = 5
WIDTH = 1280          # frames are scaled to this width (even height): small files, readable text
MARK_SECONDS = 1.5    # how long an interaction stays framed


def recorder_for(session, path: Path) -> "Recorder":
    """The recorder that fits this session: the screen where it can be grabbed, else the tab."""
    from sbtest.reporting.evidence import can_grab_screen

    if can_grab_screen(session.cfg) and session.native is not None:
        return ScreenRecorder(session, path)
    return TabRecorder(session, path)


class Recorder:
    """Common part: the frame loop, marks, step caption, ffmpeg. A subclass gives the picture
    (``_grab``) and says where an interaction is in it (``_place``)."""

    def __init__(self, session, path: Path, fps: int = FPS, width: int = WIDTH) -> None:
        self.session, self.path, self.fps, self.width = session, Path(path), fps, width
        self.size = None                        # video size, fixed by the first frame
        self.marks: list[tuple[float, dict]] = []
        self._stop = threading.Event()
        self._thread = None
        self._writer = None
        self._begun = False
        self._lock = threading.Lock()
        self.frames = 0

    # -- for subclasses ----------------------------------------------------------------
    def _begin(self) -> None:
        """Called once on the test thread before the first frame."""

    def _end(self) -> None:
        """Called once after the last frame."""

    def _grab(self):
        """The picture now (PIL image), or None to repeat the last frame."""
        raise NotImplementedError

    def _origin(self) -> tuple[int, int]:
        """Point of the marks' coordinates that is the picture's top-left corner."""
        return (0, 0)

    def _place(self, m: dict):
        """Box (left, top, right, bottom) of interaction ``m`` in the marks' coordinates, or None."""
        return m.get("screen")

    def _window_shown(self) -> bool:
        """The browser has a window to record (it starts without one: the test's first page
        opens it). Never opens one itself."""
        return getattr(self.session, "has_window", True)

    def _open(self) -> None:
        """First frame and the ffmpeg writer (the video size is the first frame's)."""
        import imageio_ffmpeg

        self._begin()
        self._begun = True
        first = self._frame()
        if first is None:
            raise RuntimeError("no first video frame")
        self.size = first.size
        self._writer = imageio_ffmpeg.write_frames(
            str(self.path), self.size, fps=self.fps, codec="libx264", quality=6, macro_block_size=2,
            pix_fmt_out="yuv420p", output_params=["-preset", "ultrafast"], ffmpeg_log_level="error")
        self._writer.send(None)
        self._writer.send(first.tobytes())
        self.frames = 1

    def _try_open(self) -> None:
        with self._lock:   # the test thread (window opened) and the video thread may both try
            if self._writer is None and not self._stop.is_set():
                self._open()

    def _on_window(self) -> None:
        """The browser opened its first window (session.window_opened): record from now on."""
        try:
            self._try_open()
        except Exception as e:  # noqa: BLE001 - recording never fails a test
            log.warning("video recording not started: %s", e)

    # -- called on the test thread ---------------------------------------------------
    def start(self) -> "Recorder":
        """Start recording; while the browser has no window yet, the video starts when it opens."""
        import imageio_ffmpeg  # noqa: F401 - fail here, not in the thread, when it is missing

        self.path.parent.mkdir(parents=True, exist_ok=True)
        listeners = getattr(self.session, "window_opened", None)
        if listeners is not None:
            listeners.append(self._on_window)
        if self._window_shown():
            self._try_open()
        self._thread = threading.Thread(target=self._loop, name="sbtest-video", daemon=True)
        self._thread.start()
        return self

    def mark(self, m: dict) -> None:
        """An interaction (steps.mark) -> framed in the next frames."""
        try:
            box = self._place(m)
        except Exception:  # noqa: BLE001 - the frame is a help, not the test
            box = None
        self.marks.append((time.monotonic(), {**m, "web": None, "screen": box}))

    def stop(self) -> Path | None:
        """Finish the file; returns its path (None when nothing was recorded)."""
        self._stop.set()
        listeners = getattr(self.session, "window_opened", None)
        if listeners is not None and self._on_window in listeners:
            listeners.remove(self._on_window)
        if self._thread is not None:
            self._thread.join(timeout=10)
        try:
            if self._begun:
                self._end()
        except Exception as e:  # noqa: BLE001 - browser already gone
            log.debug("video source not closed: %s", e)
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception as e:  # noqa: BLE001
                log.warning("video not finished: %s", e)
                return None
        return self.path if self.frames and self.path.exists() else None

    # -- background thread -------------------------------------------------------------
    def _loop(self) -> None:
        tick = 1 / self.fps
        while self._writer is None:   # no window yet: the video starts when the first page opens
            if self._stop.wait(tick):
                return
            if self._window_shown():
                try:
                    self._try_open()
                except Exception as e:  # noqa: BLE001 - e.g. the browser restarting: try again
                    log.debug("video not started yet: %s", e)
        next_t = time.monotonic() + tick
        frame = None
        while not self._stop.is_set():
            try:
                frame = self._frame() or frame
            except Exception as e:  # noqa: BLE001 - browser closing, desktop locked: keep the last frame
                log.debug("video frame skipped: %s", e)
            if frame is not None:
                # real time: when grabbing was slow, repeat the frame for the ticks it missed
                now = time.monotonic()
                repeat = 1 + max(0, int((now - next_t) / tick))
                for _ in range(repeat):
                    self._writer.send(frame.tobytes())
                    self.frames += 1
                next_t += tick * repeat
            self._stop.wait(max(0.0, next_t - time.monotonic()))

    def _frame(self):
        from PIL import Image, ImageDraw

        from sbtest.reporting.evidence import _font, draw_marks

        img = self._grab()
        if img is None:
            return None
        img = img.convert("RGB")
        now = time.monotonic()
        active = [m for t, m in self.marks if now - t < MARK_SECONDS]
        if active:
            numbered = len(self.marks) - len(active) + 1
            draw_marks(img, active, origin=self._origin(), first=numbered)
        running = [s for s in steps.history() if s["status"] == "running"]
        if running:   # the case step being executed, at the bottom
            draw = ImageDraw.Draw(img)
            font = _font(max(14, img.width // 70))
            text = running[-1]["title"]
            tw, th = draw.textbbox((0, 0), text, font=font)[2:]
            draw.rectangle((0, img.height - th - 16, min(img.width, tw + 24), img.height), fill=(30, 30, 30))
            draw.text((12, img.height - th - 10), text, fill="white", font=font)
        w = self.width
        h = (img.height * w // img.width) // 2 * 2
        img = img.resize((w, h))
        if self.size and img.size != self.size:   # the windows box changed: keep the video size
            canvas = Image.new("RGB", self.size, (40, 40, 40))
            img.thumbnail(self.size)
            canvas.paste(img, (0, 0))
            img = canvas
        return img


class ScreenRecorder(Recorder):
    """The browser's windows on the Windows desktop (native bubbles and dialogs included)."""

    def __init__(self, session, path: Path, **kw) -> None:
        super().__init__(session, path, **kw)
        self.box = None                         # screen box of the browser windows
        self._box_time = 0.0
        self._viewport: dict = {}               # window box -> page viewport origin on screen

    def _begin(self) -> None:
        self.box, self._box_time = self.session.native.window_rect(), time.monotonic()

    def _origin(self) -> tuple[int, int]:
        return self.box[:2]

    def _grab(self):
        from PIL import ImageGrab

        if not self._window_shown():   # restart: the new browser has no window yet - keep the last frame
            return None
        if time.monotonic() - self._box_time > 1:   # windows open / close (dialogs, popups)
            self.box, self._box_time = self.session.native.window_rect(), time.monotonic()
        return ImageGrab.grab(bbox=self.box, all_screens=True)

    def _place(self, m: dict):
        if m.get("web") and self.box is not None:   # page viewport origin: one UIA lookup per window position
            if self.box not in self._viewport:
                self._viewport[self.box] = self.session.native.viewport_origin()
            vx, vy = self._viewport[self.box]
            x, y, w, h, dpr = m["web"]
            return (vx + x * dpr, vy + y * dpr, vx + (x + w) * dpr, vy + (y + h) * dpr)
        return m.get("screen")


class TabRecorder(Recorder):
    """The current tab, as frames the browser sends over DevTools (works headless)."""

    def __init__(self, session, path: Path, **kw) -> None:
        super().__init__(session, path, **kw)
        self._page = None
        self._cdp = None
        self._latest: tuple[bytes, dict] | None = None   # (JPEG, metadata) of the newest frame
        self._shown = None                                # the JPEG the last picture came from
        self._image = None

    async def _on_frame(self, event: dict) -> None:
        self._latest = (base64.b64decode(event["data"]), event.get("metadata") or {})
        try:
            await self._cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
        except Exception:  # noqa: BLE001 - the tab closed
            pass

    async def _cast(self, page) -> None:
        await self._uncast()
        self._page = page
        self._cdp = await page.context.new_cdp_session(page)
        self._cdp.on("Page.screencastFrame", self._on_frame)
        await self._cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 70, "maxWidth": self.width,
                                                      "maxHeight": self.width, "everyNthFrame": 1})

    async def _uncast(self) -> None:
        cdp, self._cdp = self._cdp, None
        if cdp is not None:
            try:
                await cdp.send("Page.stopScreencast")
                await cdp.detach()
            except Exception:  # noqa: BLE001 - the tab closed
                pass

    def _begin(self) -> None:
        web = self.session.web
        web.run(self._cast(web.page), 10)
        end = time.monotonic() + 2          # the browser sends the first frame at once
        while self._latest is None and time.monotonic() < end:
            time.sleep(0.05)
        if self._latest is None:            # a tab that paints nothing: start from a screenshot
            self._latest = (web.run(web.page.screenshot(type="jpeg", quality=70), 10), {})

    def _end(self) -> None:
        web = self.session.web
        if web is not None:
            web.run(self._uncast(), 5)

    def _grab(self):
        from PIL import Image

        web = self.session.web            # None while the test restarts the browser
        if web is not None and web.has_window and web.page is not self._page and not web.page.is_closed():
            web.run(self._cast(web.page), 10)   # the test moved to another tab: follow it
        latest = self._latest
        if latest is None:
            return None
        if latest[0] is not self._shown:
            self._shown, self._image = latest[0], Image.open(BytesIO(latest[0])).convert("RGB")
        return self._image.copy()

    def _place(self, m: dict):
        if not m.get("web") or self._image is None:
            return None                     # browser UI is not in a tab's picture: listed as text
        css_width = (self._latest[1] if self._latest else {}).get("deviceWidth") or 0
        x, y, w, h, dpr = m["web"]
        f = self._image.width / css_width if css_width else dpr
        return (x * f, y * f, (x + w) * f, (y + h) * f)
