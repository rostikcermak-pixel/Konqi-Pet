"""
clip_recorder.py - records short GIF clips of Konqi doing something stupid.

Grabs a small region of the screen around the pet for a couple of seconds,
encodes it to an animated GIF on a worker thread and drops it in
~/Pictures/Konqi Moments/. The whole point is that the clips are small
enough to post somewhere.
"""
from __future__ import annotations
import logging, os, time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

try:
    from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui  import QImage, QGuiApplication
    _QT6 = True
except ImportError:
    from PyQt5.QtCore import QObject, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui  import QImage, QGuiApplication
    _QT6 = False

from PIL import Image

log = logging.getLogger("konqi.clip")

FRAME_W, FRAME_H = 480, 360      # capture box, also the output size
CAMERA_LERP      = 0.18          # how fast the box chases the pet


def output_dir() -> Path:
    base = os.environ.get("XDG_PICTURES_DIR") or str(Path.home() / "Pictures")
    return Path(base) / "Konqi Moments"


def capture_supported() -> Tuple[bool, str]:
    """Screen grabbing only works on X11/XWayland, same as window climbing."""
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" and not os.environ.get("DISPLAY"):
        return False, "Screen capture needs X11 or XWayland. Wayland says no."
    if QGuiApplication.primaryScreen() is None:
        return False, "No screen to record."
    return True, ""


def _qimage_to_pil(qimg: QImage) -> Image.Image:
    fmt = QImage.Format.Format_RGB888 if _QT6 else QImage.Format_RGB888
    qimg = qimg.convertToFormat(fmt)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.constBits()
    nbytes = qimg.sizeInBytes() if hasattr(qimg, "sizeInBytes") else qimg.byteCount()
    ptr.setsize(nbytes)
    return Image.frombuffer("RGB", (w, h), bytes(ptr), "raw", "RGB", qimg.bytesPerLine(), 1)


class _EncodeThread(QThread):
    done   = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, frames: List[Image.Image], path: Path, fps: int):
        super().__init__()
        self._frames = frames
        self._path   = path
        self._fps    = fps

    def run(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            palette = self._frames[0].quantize(colors=128, method=Image.MEDIANCUT)
            frames  = [f.quantize(palette=palette, dither=Image.FLOYDSTEINBERG)
                       for f in self._frames]
            frames[0].save(self._path, save_all=True, append_images=frames[1:],
                           duration=int(1000 / self._fps), loop=0, optimize=True)
            self.done.emit(str(self._path))
        except Exception as exc:
            log.warning("Clip encode failed: %s", exc)
            self.failed.emit(str(exc))


class ClipRecorder(QObject):
    """One recorder per app. Records at most one clip at a time."""

    saved  = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, parent=None, fps: int = 12, seconds: float = 3.0):
        super().__init__(parent)
        self._fps      = max(5, min(20, int(fps)))
        self._seconds  = max(1.0, min(8.0, float(seconds)))
        self._frames: List[Image.Image] = []
        self._timer: Optional[QTimer]   = None
        self._encoder: Optional[_EncodeThread] = None
        self._center: Optional[Tuple[float, float]] = None
        self._rect_fn: Optional[Callable[[], Tuple[int, int, int, int]]] = None
        self._label = "moment"

    @property
    def busy(self) -> bool:
        return self._timer is not None or (self._encoder is not None and self._encoder.isRunning())

    def start(self, rect_fn: Callable[[], Tuple[int, int, int, int]], label: str = "moment") -> bool:
        """rect_fn returns the pet's (x, y, w, h) in global coords, called per frame."""
        if self.busy:
            return False
        ok, reason = capture_supported()
        if not ok:
            self.failed.emit(reason)
            return False

        self._rect_fn = rect_fn
        self._label   = "".join(c if c.isalnum() else "-" for c in label).strip("-") or "moment"
        self._frames  = []
        self._center  = None

        self._timer = QTimer(self)
        self._timer.setInterval(max(1, int(1000 / self._fps)))
        self._timer.timeout.connect(self._grab)
        self._timer.start()
        return True

    def _grab(self):
        try:
            screen = QGuiApplication.primaryScreen()
            geo    = screen.geometry()
            kx, ky, kw, kh = self._rect_fn()
            target = (kx + kw / 2.0, ky + kh / 2.0)
            if self._center is None:
                self._center = target
            else:
                self._center = (self._center[0] + (target[0] - self._center[0]) * CAMERA_LERP,
                                self._center[1] + (target[1] - self._center[1]) * CAMERA_LERP)

            x = int(self._center[0] - FRAME_W / 2)
            y = int(self._center[1] - FRAME_H / 2)
            x = max(geo.x(), min(x, geo.x() + geo.width()  - FRAME_W))
            y = max(geo.y(), min(y, geo.y() + geo.height() - FRAME_H))

            shot = screen.grabWindow(0, x, y, FRAME_W, FRAME_H)
            self._frames.append(_qimage_to_pil(shot.toImage()))
        except Exception as exc:
            log.warning("Frame grab failed: %s", exc)
            self._finish_capture(abort=True)
            self.failed.emit("Could not grab the screen.")
            return

        if len(self._frames) >= int(self._seconds * self._fps):
            self._finish_capture()

    def _finish_capture(self, abort: bool = False):
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        if abort or len(self._frames) < 2:
            self._frames = []
            return

        path = output_dir() / f"konqi-{self._label}-{time.strftime('%Y%m%d-%H%M%S')}.gif"
        self._encoder = _EncodeThread(self._frames, path, self._fps)
        self._encoder.done.connect(self.saved)
        self._encoder.failed.connect(self.failed)
        self._encoder.finished.connect(self._clear_encoder)
        self._encoder.start()
        self._frames = []

    def _clear_encoder(self):
        self._encoder = None

    def stop(self):
        self._finish_capture(abort=True)
        if self._encoder is not None and self._encoder.isRunning():
            self._encoder.wait(3000)
