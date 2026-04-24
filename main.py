                      
"""
main.py – Konqi Shimeji: Chaotic Gremlin Edition

A deliberately annoying, sarcastic, interactive desktop companion.
Usage:
    python3 main.py [--debug] [--hyper] [--count N] [--quiet] [--no-chaos]
"""
from __future__ import annotations
import argparse, json, logging, math, os, random, select, subprocess, sys, time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PyQt6.QtCore    import Qt, QTimer, QPoint, QSize, pyqtSignal, QThread, pyqtSlot
    from PyQt6.QtGui     import (QPixmap, QImage, QColor, QBitmap, QPainter,
                                  QRegion, QCursor, QIcon, QAction, QFont,
                                  QPen, QBrush, QPainterPath, QFontMetrics)
    from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                                  QSystemTrayIcon, QDialog, QVBoxLayout,
                                  QHBoxLayout, QPushButton, QCheckBox,
                                  QDialogButtonBox)
    _QT6 = True
except ImportError:
    try:
        from PyQt5.QtCore    import Qt, QTimer, QPoint, QSize, pyqtSignal, QThread, pyqtSlot
        from PyQt5.QtGui     import (QPixmap, QImage, QColor, QBitmap, QPainter,
                                      QRegion, QCursor, QIcon, QFont,
                                      QPen, QBrush, QPainterPath, QFontMetrics)
        from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                                      QSystemTrayIcon, QDialog, QVBoxLayout,
                                      QHBoxLayout, QPushButton, QCheckBox,
                                      QDialogButtonBox, QAction)
        _QT6 = False
    except ImportError:
        print("ERROR: PyQt6 or PyQt5 is required."); sys.exit(1)

from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from animation     import AnimationController, State
from physics       import PhysicsEngine, Rect, get_screen_rect_qt
from autostart     import enable as autostart_enable
from autostart     import disable as autostart_disable
from autostart     import is_enabled as autostart_is_enabled
from sprite_loader import load_sprites, get_cached_animations
from chaos_gremlin import GremlinBrain, GremlinEvent
from sound_engine  import SoundEngine
from dialog_system import DialogSystem
from pet_state     import PetState, PetStateMachine

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("konqi.main")

CONFIG_PATH = HERE / "config.json"
ASSETS_DIR  = HERE / "assets"

def load_config() -> dict:
    defaults = dict(
        behavior_mode="calm", animation_speed=1.0, spawn_count=1, fps=60,
        cpu_reactions=True, cpu_high_threshold=85, sound_effects=False,
        always_on_top=True, multi_monitor=False, sprite_height_px=96,
        debug_mode=False, chaos_mode=True, quiet_mode=False,
    )
    try:
        data = json.loads(CONFIG_PATH.read_text())
        defaults.update({k: v for k, v in data.items() if not k.startswith("_")})
    except Exception:
        pass
    return defaults

def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as exc:
        log.warning("Could not save config: %s", exc)

def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height,
                  QImage.Format.Format_RGBA8888 if _QT6 else QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

def make_mask_from_pixmap(pixmap: QPixmap) -> QBitmap:
    return pixmap.createMaskFromColor(
        QColor(0, 0, 0, 0),
        Qt.MaskMode.MaskInColor if _QT6 else Qt.MaskInColor,
    )

                                                                             
                                                         
                                                                             
class DialogueBubble(QWidget):
    """
    Speech bubble that tracks its owner KonqiWindow every frame.

    Rotation modes
    --------------
    "normal"        – tail points down-centre, bubble sits above Konqi
    "climb_right"   – whole bubble rotated 90° CCW (text reads upward);
                      tail points left toward the right-side wall
    "climb_left"    – whole bubble rotated 90° CW (text reads downward);
                      tail points right toward the left-side wall

    The window is always sized to fit the ROTATED content so Qt never
    clips anything.  We do the rotation manually inside paintEvent so
    we have full control over tail direction and placement.
    """

    BUBBLE_COLORS = [
        ("#FF6B6B", "#2D1B1B"), ("#FFD93D", "#2D2400"), ("#6BCB77", "#0D2B10"),
        ("#4D96FF", "#0A1A3A"), ("#FF922B", "#2D1400"), ("#CC5DE8", "#1E0A2D"),
    ]

                         
    TAIL = 8                                           
    TAIL_LEN = 8                                       
    GAP  = 4                                        

    def __init__(self, text: str, screen_rect: Rect, duration_ms: int = 4500):
        super().__init__()
        flags = (Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool |
                 Qt.WindowType.WindowTransparentForInput)
        if _QT6:
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._screen    = screen_rect
        self._bg_color, self._text_color = random.choice(self.BUBBLE_COLORS)
        self._alpha     = 255
        self._dead      = False
        self._rotation  = "normal"                                            
        self._text      = text                               

                                                                          
        self._font = QFont("monospace", 9, QFont.Weight.Bold)           
        fm   = QFontMetrics(self._font)
        max_w = 200                                                       
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if fm.horizontalAdvance(test) > max_w and cur:
                lines.append(cur); cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
        self._lines = lines
        self._lh    = fm.height() + 2
        self._pad   = 8                                                  

                                               
        self._bw = min(max_w + self._pad*2,
                       max((fm.horizontalAdvance(l) for l in lines), default=60) + self._pad*2)
        self._bh = len(lines) * self._lh + self._pad*2              
                                                 
        self._lw = self._bw                                     
        self._ll = self._bh + self.TAIL_LEN                                    

                                                          
        self.resize(self._lw, self._ll)
        self.hide()                                   

                                                                            
        self._life = QTimer(self); self._life.setSingleShot(True)
        self._life.timeout.connect(self._start_fade)
        self._life.start(max(1500, duration_ms - 800))
        self._fade = QTimer(self); self._fade.setInterval(30)
        self._fade.timeout.connect(self._fade_step)

                                                                        
                                                     
                                                                        

    def reposition(self, konqi_x: int, konqi_y: int,
                   konqi_w: int, konqi_h: int,
                   anim_state: "State",
                   stack_index: int = 0) -> None:
        """Move and resize the bubble to track Konqi, respecting his state.

        stack_index=0 is closest to Konqi, higher indices stack further away.
        """
        if self._dead:
            return

        climbing_right = (anim_state == State.CLIMB_RIGHT)
        climbing_left  = (anim_state == State.CLIMB_LEFT)

        if climbing_right:
            rot = "climb_right"
        elif climbing_left:
            rot = "climb_left"
        else:
            rot = "normal"

        rotation_changed = (rot != self._rotation)
        self._rotation = rot

                                            
        if rot == "normal":
            win_w, win_h = self._lw, self._ll
        else:
                                                                   
            win_w, win_h = self._ll, self._lw

        if rotation_changed:
            self.resize(win_w, win_h)

                                                           
        scr = self._screen
        ANCHOR_GAP = 4                                                

        if rot == "normal":
            cx = konqi_x + konqi_w // 2
                                                                    
            stack_offset = stack_index * (win_h + self.GAP)
            cy = konqi_y - ANCHOR_GAP - stack_offset
            bx = cx - win_w // 2
            by = cy - win_h
            bx = max(scr.x, min(bx, scr.right  - win_w))
            by = max(scr.y, min(by, scr.bottom - win_h))

        elif rot == "climb_right":
            cx = konqi_x - ANCHOR_GAP
            cy = konqi_y + konqi_h // 2
                                            
            stack_offset = stack_index * (win_w + self.GAP)
            bx = cx - win_w - stack_offset
            by = cy - win_h // 2
            bx = max(scr.x, min(bx, scr.right  - win_w))
            by = max(scr.y, min(by, scr.bottom - win_h))

        else:              
            cx = konqi_x + konqi_w + ANCHOR_GAP
            cy = konqi_y + konqi_h // 2
                                            
            stack_offset = stack_index * (win_w + self.GAP)
            bx = cx + stack_offset
            by = cy - win_h // 2
            bx = max(scr.x, min(bx, scr.right  - win_w))
            by = max(scr.y, min(by, scr.bottom - win_h))

        self.resize(win_w, win_h)
        self.move(bx, by)
        if not self.isVisible():
            self.show()
        self.update()

                                                                        
                    
                                                                        

    def _start_fade(self):
        self._fade.start()

    def _fade_step(self):
        self._alpha -= 15
        if self._alpha <= 0:
            self._fade.stop()
            self._dismiss()
        else:
            self.update()

    def _dismiss(self):
        if self._dead:
            return
        self._dead = True
        self.hide()
        self.deleteLater()

    def is_alive(self) -> bool:
        return not self._dead

                                                                        
           
                                                                        

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._alpha / 255.0)

        win_w = self.width()
        win_h = self.height()
        bg    = QColor(self._bg_color)
        rot   = self._rotation

                                                                              
                                                                             

        lw = self._lw
        bh = self._bh
        ll = self._ll

        if rot == "normal":
                                 
            pass
        elif rot == "climb_right":
                                                                   
                                                          
            p.translate(0, win_h)
            p.rotate(-90)
                                                                  
        else:              
                                                                
            p.translate(win_w, 0)
            p.rotate(90)

                                                 

                
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 50)))
        p.drawRoundedRect(3, 3, lw-2, bh-2, 10, 10)

              
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor("#FFFFFF"), 1.5))
        p.drawRoundedRect(0, 0, lw-1, bh-1, 10, 10)

                                                          
        tx = lw // 2
        tail_path = QPainterPath()
        tail_path.moveTo(tx - self.TAIL, bh - 1)
        tail_path.lineTo(tx + self.TAIL, bh - 1)
        tail_path.lineTo(tx,             ll - 1)
        tail_path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawPath(tail_path)

              
        p.setFont(self._font)
        p.setPen(QPen(QColor(self._text_color)))
        for i, line in enumerate(self._lines):
            p.drawText(self._pad,
                       self._pad + i * self._lh + self._lh - 2,
                       line)

        p.end()

                                                                             
                
                                                                             
class SpriteLoaderThread(QThread):
    done = pyqtSignal(dict)
    def __init__(self, force=False): super().__init__(); self._force = force
    def run(self):
        anims = get_cached_animations(ASSETS_DIR)
        if anims is None or self._force:
            anims = load_sprites(ASSETS_DIR, force_download=self._force)
        self.done.emit(anims)

class CPUMonitor(QThread):
    cpu_level = pyqtSignal(float)
    def __init__(self, interval=5.0): super().__init__(); self._interval=interval; self._running=True
    def run(self):
        while self._running:
            if _PSUTIL:
                try: self.cpu_level.emit(float(psutil.cpu_percent(interval=self._interval)))
                except Exception: pass
            else: self.msleep(int(self._interval * 1000))
    def stop(self): self._running = False

                                                                             
                                               
                                                                             
class ScribbleWidget(QWidget):
    """A transparent, click-through doodle that appears on the desktop then fades."""
    WORDS = [
        "hi", "??", "ugh", "...", "ok", "nope", "fine",
        "why", "help", "no", "yes?", "hmm", "zzz", ":(",
        "lol", "nah", "k", "ew", "hm", "bruh",
    ]
    COLORS = ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF","#FF922B","#CC5DE8","#FF69B4"]

    def __init__(self, anchor: QPoint, screen_rect: Rect):
        super().__init__()
        flags = (Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool |
                 Qt.WindowType.WindowTransparentForInput)
        if _QT6: flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                                                                                  
        self._dead = False

        self._alpha = 230
        self._color = QColor(random.choice(self.COLORS))
        self._word  = random.choice(self.WORDS)
        self._scr   = screen_rect

                                 
        size_w, size_h = 140, 120
                                                                
        self._points = [(random.randint(8, size_w-8), random.randint(8, size_h-28))
                        for _ in range(8)]

        bx = max(screen_rect.x, min(anchor.x() - size_w//2, screen_rect.right  - size_w))
        by = max(screen_rect.y, min(anchor.y() - size_h - 5, screen_rect.bottom - size_h))
        self.resize(size_w, size_h)
        self.move(bx, by)
        self.show()
        self.raise_()

        self._fade = QTimer(self); self._fade.setInterval(35)
        self._fade.timeout.connect(self._fade_step)
        QTimer.singleShot(2200, self._fade.start)

    def _fade_step(self):
        self._alpha -= 10
        if self._alpha <= 0:
            self._fade.stop()
            self._dead = True
            self.hide()
            self.deleteLater()
        else:
            self.update()

    def is_alive(self) -> bool:
        return not self._dead

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._alpha / 255.0)
                                
        pen = QPen(self._color, 3, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        pts = self._points
        for i in range(len(pts)-1):
            p.drawLine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
                               
        p.setFont(QFont("monospace", 13, QFont.Weight.Bold))
        p.drawText(6, self.height()-8, self._word)
        p.end()

                                                                             
             
                                                                             


class InteractiveBubble(QWidget):
    """
    Speech bubble with two clickable response buttons.

    Unlike DialogueBubble this widget receives mouse input (no
    WindowTransparentForInput) so the player can click the buttons.
    The on_response callback receives the outcome string: "happy",
    "satisfied", or "angry".
    """

    _BG      = "#1a0a2e"
    _BORDER  = "#CC5DE8"
    _TEXT    = "#FFD93D"
    _BTN_BG  = "#2D1B4E"
    _BTN_HOV = "#3D2B6E"
    _TIMEOUT_MS = 15_000

    def __init__(self, dialog: dict, screen_rect: Rect, on_response) -> None:
        super().__init__()
        flags = (Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool)
        if _QT6:
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._screen      = screen_rect
        self._on_response = on_response
        self._dead        = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 18)
        outer.setSpacing(8)

        lbl = QLabel(dialog["text"])
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("monospace", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{self._TEXT}; background:transparent;")
        lbl.setFixedWidth(210)
        outer.addWidget(lbl)

        btn_style = (
            f"QPushButton{{background:{self._BTN_BG};color:{self._TEXT};"
            f"border:1px solid {self._BORDER};border-radius:6px;"
            f"padding:5px 8px;font-size:9pt;font-family:monospace;}}"
            f"QPushButton:hover{{background:{self._BTN_HOV};}}"
        )
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for choice in dialog["choices"]:
            b = QPushButton(choice["text"])
            b.setStyleSheet(btn_style)
            b.setFixedHeight(30)
            b.clicked.connect(lambda _=False, r=choice["result"]: self._respond(r))
            btn_row.addWidget(b)
        outer.addLayout(btn_row)

        self.adjustSize()
        self.hide()

        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._dismiss)
        self._timeout.start(self._TIMEOUT_MS)

    def paintEvent(self, ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        tail = 10
        bubble_h = h - tail

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawRoundedRect(3, 3, w - 2, bubble_h - 2, 10, 10)

        p.setBrush(QBrush(QColor(self._BG)))
        p.setPen(QPen(QColor(self._BORDER), 1.5))
        p.drawRoundedRect(0, 0, w - 1, bubble_h - 1, 10, 10)

        cx = w // 2
        path = QPainterPath()
        path.moveTo(cx - 7, bubble_h - 1)
        path.lineTo(cx + 7, bubble_h - 1)
        path.lineTo(cx,     h - 1)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self._BG)))
        p.drawPath(path)
        p.end()

    def reposition(self, kx: int, ky: int, kw: int, kh: int) -> None:
        bx = kx + kw // 2 - self.width() // 2
        by = ky - self.height() - 6
        scr = self._screen
        bx = max(scr.x, min(bx, scr.right  - self.width()))
        by = max(scr.y, min(by, scr.bottom - self.height()))
        self.move(bx, by)
        if not self.isVisible():
            self.show()

    def _respond(self, outcome: str) -> None:
        if self._dead:
            return
        self._dead = True
        self._timeout.stop()
        self.hide()
        self.deleteLater()
        self._on_response(outcome)

    def _dismiss(self) -> None:
        if self._dead:
            return
        self._dead = True
        self.hide()
        self.deleteLater()

    def is_alive(self) -> bool:
        return not self._dead

class KonqiWindow(QWidget):
    spawn_requested = pyqtSignal()
    exit_requested  = pyqtSignal()

    def __init__(self, animations, screen_rect, config, parent_app, gremlin):
        super().__init__()
        self._app_ref       = parent_app
        self._cfg           = config
        self._anims         = animations
        self._dialog_system = parent_app.dialog_system
        self._pet_state     = parent_app.pet_state
        self._screen  = screen_rect
        self._gremlin = gremlin

        self._anim = AnimationController(
            animations,
            fps=config["fps"],
            behavior_mode=config["behavior_mode"],
            on_state_change=self._on_anim_state_change,
        )
        self._anim.speed = float(config["animation_speed"])

        start_x = random.randint(screen_rect.x + 50,
                                  max(screen_rect.x+51, screen_rect.right-150))
        self._physics = PhysicsEngine(screen_rect, initial_x=float(start_x),
                                       initial_y=float(screen_rect.bottom-120))
        self._physics.state.on_ground = False
                                                                            
        try:
            from sprite_loader import get_climb_canvas_size
            ccw, _ = get_climb_canvas_size(animations)
            self._physics.set_climb_canvas_w(ccw)
        except Exception:
            pass

        self._dragging       = False
        self._drag_offset    = QPoint(0, 0)
        self._cpu_tired      = False
        self._chaos_mode     = config.get("chaos_mode", True)
        self._quiet_mode     = config.get("quiet_mode", False)
        self._spinning       = False
        self._spin_timer: Optional[QTimer] = None
        self._drift_target_x: Optional[float] = None
        self._drift_speed   = 0.0
        self._active_bubbles: List[DialogueBubble] = []
        self._interactive_bubble: Optional[InteractiveBubble] = None
        self._last_tick_time = time.time()
        self._sound = SoundEngine(enabled=config.get('sound_effects', False))
        self._flee_active = False
        self._sit_active  = False
        self._sit_target_y: Optional[float] = None

        flags = (Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        if _QT6: flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_sprite()
        self.move(int(self._physics.state.x), int(self._physics.state.y))
        self.show()

        self._timer = QTimer(self)
        self._timer.setInterval(max(8, 1000 // config["fps"]))
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        if self._chaos_mode:
            self._gremlin_timer = QTimer(self)
            self._gremlin_timer.setInterval(4000)
            self._gremlin_timer.timeout.connect(self._gremlin_tick)
            self._gremlin_timer.start()

    @pyqtSlot()
    def _tick(self):
        frame_changed = self._anim.tick()
        if not self._dragging:
            self._sync_physics()
            self._apply_drift()
        nx, ny = int(self._physics.state.x), int(self._physics.state.y)
        if (nx, ny) != (self.x(), self.y()):
            self.move(nx, ny)
        if frame_changed:
            self._update_sprite()
            if self._anim.state in (State.WALK_RIGHT, State.WALK_LEFT):
                if self._anim._frame_idx % 4 == 0: self._sound.footstep()
            elif self._anim.state in (State.CLIMB_RIGHT, State.CLIMB_LEFT):
                if self._anim._frame_idx % 4 == 0: self._sound.climb_tap()
                           
        if self._flee_active:
            self._update_flee()
                             
        if self._sit_active:
            self._update_sit()
                                                                      
                                                                             
        cur_state = self._anim.state
        kx, ky, kw, kh = self.x(), self.y(), self.width(), self.height()
        live = []
        for b in self._active_bubbles:
            if b.is_alive():
                live.append(b)
        self._active_bubbles = live
        for stack_idx, b in enumerate(reversed(live)):
            b.reposition(kx, ky, kw, kh, cur_state, stack_index=stack_idx)
        if self._interactive_bubble and self._interactive_bubble.is_alive():
            self._interactive_bubble.reposition(kx, ky, kw, kh)

    @pyqtSlot()
    def _gremlin_tick(self):
        if not self._chaos_mode: return
        now = time.time(); dt = now - self._last_tick_time; self._last_tick_time = now
        mouse_pos = None
        try:
            c = QCursor.pos(); mouse_pos = (c.x(), c.y())
        except Exception: pass
        self._gremlin.tick(delta_seconds=dt, mouse_pos=mouse_pos)
                                          
        try:
            win = __import__('chaos_gremlin').get_focused_window_name() or ''
            if any(k in win for k in ['chaos_gremlin','main.py','sprite_loader','konqi-shimeji'])\
                    and not getattr(self,'_src_reacted',False):
                self._src_reacted = True
                self._gremlin.notify_source_code_opened()
        except Exception: pass
        for ev in sorted(self._gremlin.consume_events(), key=lambda e: -e.priority):
            if ev.kind in ("dialogue", "tip", "hardware_roast"):
                self._show_bubble(ev.text)
            elif ev.kind == "chaos_action":
                self._do_chaos_action(ev.action)
        # ----------------------------------------------------------
        # State tick: auto-returns the pet to IDLE after its duration
        # expires. This is where state-based behavior re-syncs so the
        # main loop never blocks.
        # ----------------------------------------------------------
        if self._pet_state.tick():
            self._apply_state_behavior()
        if self._pet_state.dialog_ready() and random.random() < 0.30:
            self._trigger_interactive_dialog()

    def _sync_physics(self):
        # State-driven speed is applied to the physics engine here, once
        # per tick. The physics engine reads this value via its own state.
        s = self._physics.state
        s.behavior_mode    = self._cfg["behavior_mode"]
        s.speed_multiplier = self._pet_state.speed_multiplier
        anim_st = self._anim.state
        if anim_st == State.WALK_RIGHT: s.walk_dir = 1
        elif anim_st == State.WALK_LEFT: s.walk_dir = -1

                                                                       
                                                                                
        VOLUNTARY_PAUSE = frozenset({
            State.SLEEP, State.STRETCH, State.FLY, State.DRAG,
            State.LOOK_AROUND, State.WAVE,
        })

                                                           
        if anim_st == State.IDLE:
            s.vx = 0.0
            s.climbing = False
            if s.on_ground:
                s.vy = 0.0
                return
            anim_key, _ = self._physics.update()
            if anim_key == "fall":
                self._anim.set_state(State.FALL)
            return

        if anim_st in VOLUNTARY_PAUSE:
            s.vx = 0.0
            s.climbing = False                                               
            if s.on_ground:
                s.vy = 0.0
                return
                                                                            
            anim_key, _ = self._physics.update()
            if anim_key == "fall" and anim_st != State.FALL:
                self._anim.set_state(State.FALL)
                                                                          
            return

        anim_key, _ = self._physics.update()
        if anim_key == "fall":
            if anim_st != State.FALL: self._anim.set_state(State.FALL)
        elif anim_key in ("climb_right", "climb_left"):
            target = State.CLIMB_RIGHT if anim_key == "climb_right" else State.CLIMB_LEFT
            if anim_st != target: self._anim.set_state(target)
        elif anim_key in ("walk_right", "walk_left"):
            target = State.WALK_RIGHT if anim_key == "walk_right" else State.WALK_LEFT
            if anim_st not in (State.FALL, State.DRAG, State.SLEEP,
                               State.CLIMB_RIGHT, State.CLIMB_LEFT,
                               State.LOOK_AROUND, State.WAVE):
                if anim_st != target: self._anim.set_state(target)
        if (self._anim.state == State.FALL and self._physics.state.on_ground
                and self._physics.state.vy == 0):
            self._anim.set_state(State.IDLE)

    def _apply_drift(self):
        if self._drift_target_x is None: return
        s = self._physics.state
        remaining = self._drift_target_x - s.x
        if abs(remaining) < 4:
            s.x = self._drift_target_x
            self._drift_target_x = None; self._drift_speed = 0.0
            self._anim.set_state(State.IDLE, force=True)
            return
                                   
        if abs(remaining) < 80:
            self._drift_speed = max(3.0, abs(self._drift_speed) * 0.88) * (1 if self._drift_speed > 0 else -1)
                                         
        if self._drift_speed > 0:
            self._anim.set_state(State.WALK_RIGHT, force=True) if s.walk_dir != 1 else None
            s.walk_dir = 1
        else:
            self._anim.set_state(State.WALK_LEFT, force=True) if s.walk_dir != -1 else None
            s.walk_dir = -1
        s.x = max(float(self._screen.x),
                  min(s.x + self._drift_speed, float(self._screen.right - self.width())))

    def _do_chaos_action(self, action: str):
        dispatch = {
            "teleport":     self._do_teleport,
            "spin":         self._do_spin,
            "drift":        self._do_drift,
            "shake":        self._do_shake,
            "dive":         self._do_dive,
            "bounce":       self._do_bounce,
            "flee_cursor":  self._start_flee_cursor,
            "sit_on_window":self._try_sit_on_window,
            "scribble":     self._do_scribble,
            "summon_twin":  lambda: self._app_ref.summon_twin(self),
            "trip":         self._do_trip,
            "stare_spot":   self._do_stare_spot,
            "freeze_glitch":self._do_freeze_glitch,
            "poem":         self._do_poem,
            "letter":       self._do_letter,
            "window_catch": self._do_window_catch,
        }
        fn = dispatch.get(action)
        if fn: fn()

                                                                              
    def _do_teleport(self):
        """Vanish with a shake, pop back somewhere else with a landing bounce."""
                                                             
        ox, oy = int(self._physics.state.x), int(self._physics.state.y)
        shake_n = [0]
        t1 = QTimer(self)
        def shake_out():
            shake_n[0] += 1
            if shake_n[0] > 8:
                t1.stop(); t1.deleteLater()
                self.hide()
                                              
                QTimer.singleShot(300, self._teleport_land)
            else:
                self.move(ox + random.randint(-5,5), oy + random.randint(-4,4))
        t1.timeout.connect(shake_out); t1.start(40)

    def _teleport_land(self):
        nx = random.randint(self._screen.x + 20, max(self._screen.x+21, self._screen.right - self.width() - 20))
        ny = self._screen.bottom - self.height()
        self._physics.teleport(float(nx), float(ny))
        self.move(nx, ny)
        self.show()
                                 
        self._physics.state.vy = -8.0
        self._physics.state.on_ground = False
        self._sound.bounce()
        QTimer.singleShot(200, lambda: self._show_bubble(random.choice([
            "Somewhere else now.", "New coordinates. Same opinion of you.",
            "Over here.", "That was uncomfortable.", "Didn't ask. Still happened.",
        ])))

                                                                              
    def _do_spin(self):
        """Accelerating spin: slow → fast → slow, ends facing original direction."""
        if self._spinning: return
        self._spinning = True
                                                                                       
        timings = [120, 100, 80, 65, 55, 50, 50, 55, 65, 80, 100, 120]
        dirs    = [1,-1,1,-1,1,-1,1,-1,1,-1,1,-1]
        step_n  = [0]
        original_dir = self._physics.state.walk_dir

        def do_step():
            i = step_n[0]
            if i >= len(timings):
                self._spinning = False
                                                         
                self._physics.state.walk_dir = original_dir
                self._anim.set_state(
                    State.WALK_RIGHT if original_dir > 0 else State.WALK_LEFT, force=True)
                return
            self._physics.state.walk_dir = dirs[i]
            self._anim.set_state(
                State.WALK_RIGHT if dirs[i] > 0 else State.WALK_LEFT, force=True)
            step_n[0] += 1
            QTimer.singleShot(timings[i], do_step)

        self._show_bubble(random.choice([
            "Spinning.", "I have no control over this.", "Rotating.",
            "This is fine.", "Going in circles. Like everything else.",
        ]))
        do_step()

                                                                              
    def _do_drift(self):
        """Dash to the opposite side with eased acceleration then deceleration."""
        s = self._physics.state
        if s.walk_dir > 0:
            self._drift_target_x = float(self._screen.right - self.width() - 5)
        else:
            self._drift_target_x = float(self._screen.x + 5)
                                                                 
        self._drift_speed = (18.0 if s.walk_dir > 0 else -18.0)
        self._show_bubble(random.choice([
            "Making a point.", "Watch this.", "Going now.",
            "Bye.", "Speed is a choice I'm making.",
        ]))

                                                                              
    def _do_shake(self):
        """Escalating panic shake: starts small, grows, then snaps back."""
        ox, oy = int(self._physics.state.x), int(self._physics.state.y)
        self._anim.set_state(State.DRAG, force=True)
        frames = [0]
        shake_t = QTimer(self)
                                                     
        profile = [2,3,5,7,9,10,9,8,6,4,4,6,8,9,7,5,3,2,1,0]
        def do_shake():
            i = frames[0]
            if i >= len(profile):
                shake_t.stop(); shake_t.deleteLater()
                self.move(ox, oy)
                self._physics.state.x = float(ox)
                self._anim.set_state(State.IDLE, force=True)
                return
            amp = profile[i]
            angle = i * 2.5                                       
            dx = int(amp * math.cos(angle))
            dy = int(amp * math.sin(angle) * 0.5)
            self.move(ox + dx, oy + dy)
            frames[0] += 1
        shake_t.timeout.connect(do_shake); shake_t.start(30)
        self._show_bubble(random.choice([
            "Something is happening to me.", "This is against my will.",
            "I don't know what this is.", "I have concerns.",
            "UNACCEPTABLE.", "Fine, apparently.",
        ]))

                                                                              
    def _do_dive(self):
        """Launch upward with rotation effect, comes back down naturally."""
        s = self._physics.state
        s.vy = -16.0
        s.vx = random.choice([-4.0, -2.5, 2.5, 4.0])
        s.on_ground = False
        self._anim.set_state(State.FLY, force=True)
        self._sound.bounce()
        self._show_bubble(random.choice([
            "Going up.", "Gravity is advisory.", "Brief vertical excursion.",
            "I have decided to leave.", "UP.",
        ]))
                                                                      

                                                                              
    def _do_bounce(self):
        """Series of 3 decreasing bounces."""
        s = self._physics.state
        bounce_n = [0]
        heights  = [-11.0, -7.0, -4.5]

        def do_next_bounce():
            if bounce_n[0] >= len(heights): return
            s.vy = heights[bounce_n[0]]
            s.on_ground = False
            self._sound.bounce()
            bounce_n[0] += 1
                                                 
            QTimer.singleShot(500, do_next_bounce)

        do_next_bounce()
        self._show_bubble(random.choice([
            "Boing. Boing. Boing.", "Three bounces. That's the rule.",
            "The floor and I have a relationship.", "Physics again.",
            "I'm doing this on purpose.",
        ]))

    def _start_flee_cursor(self):
        """Run away from cursor — moves both X and Y, uses walk animation."""
        if self._flee_active: return
        self._flee_active = True
        self._flee_timer = 0.0
        self._flee_duration = random.uniform(3.0, 5.0)
        self._show_bubble(random.choice([
            "Stay away.", "Personal space.", "Do NOT.",
            "I see you.", "Back off.", "I'm watching that cursor.",
            "No.", "I know what you're doing.",
        ]))

    def _stop_flee(self):
        self._flee_active = False

    def _update_flee(self):
        try:
            cursor = QCursor.pos()
            cx, cy = cursor.x(), cursor.y()
            mx = self.x() + self.width() // 2
            my = self.y() + self.height() // 2
            dx = mx - cx; dy = my - cy
            dist = max(1, math.sqrt(dx*dx + dy*dy))

                                                                  
            self._flee_timer = getattr(self, '_flee_timer', 0.0) + 0.016
            if self._flee_timer > getattr(self, '_flee_duration', 4.0) or dist > 400:
                self._flee_active = False
                return

            if dist < 300:
                speed = min(14.0, 3000.0 / max(dist, 1))
                                                    
                s = self._physics.state
                s.x = max(float(self._screen.x),
                          min(s.x + (dx / dist) * speed,
                              float(self._screen.right - self.width())))
                                                                                
                if cy < my and s.on_ground:
                    s.vy = -4.0
                    s.on_ground = False
                                                                
                if dx > 0:
                    self._anim.set_state(State.WALK_RIGHT, force=True)
                    s.walk_dir = 1
                else:
                    self._anim.set_state(State.WALK_LEFT, force=True)
                    s.walk_dir = -1
        except Exception:
            pass

    def _try_sit_on_window(self):
        """Try to park Konqi on top of a visible window."""
        try:
            import subprocess as sp
            result = sp.run(["xdotool", "search", "--onlyvisible", "--name", ""],
                           capture_output=True, text=True, timeout=1)
        except Exception:
            return
        if not self._physics._windows:
            return
        candidates = [w for w in self._physics._windows
                      if w.top > self._screen.top + 50
                      and w.top < self._screen.bottom - 100
                      and w.right - w.left > 200]
        if not candidates:
            return
        target = random.choice(candidates)
                                                   
        nx = random.randint(target.left, max(target.left+1, target.right - self.width()))
        ny = target.top - self.height()
        nx = max(self._screen.x, min(nx, self._screen.right - self.width()))
        ny = max(self._screen.y, ny)
        self._physics.teleport(float(nx), float(ny))
        self.move(nx, ny)
        self._sit_active = True
        self._sit_target_y = float(ny)
        self._anim.set_state(State.IDLE, force=True)
        self._show_bubble(random.choice([
            "Found a good spot.", "Nice view from up here.",
            "This window looks load-bearing.", "I live here now.",
            "Don't mind me.", "Comfortable.",
        ]))
        QTimer.singleShot(4000, self._stop_sit)

    def _stop_sit(self):
        self._sit_active = False
        self._sit_target_y = None

    def _update_sit(self):
                                                           
        if self._sit_target_y is not None:
            self._physics.state.y = self._sit_target_y
            self._physics.state.vy = 0.0
            self._physics.state.on_ground = True

    def _do_scribble(self):
        """Spawn 2-3 scribble widgets on screen. Keep references so they aren't GC'd."""
        self._sound.scribble()
                                                                             
        if not hasattr(self, '_scribbles'):
            self._scribbles: List[ScribbleWidget] = []
                         
        self._scribbles = [s for s in self._scribbles if s.is_alive()]

        count = random.randint(2, 4)
        kx = self.x() + self.width() // 2
        ky = self.y()
        scr = self._screen
        for _ in range(count):
                                                         
            sx = random.randint(scr.x + 20, scr.right  - 160)
            sy = random.randint(scr.y + 20, scr.bottom - 140)
            anchor = QPoint(sx + 70, sy + 60)
            w = ScribbleWidget(anchor, scr)
            self._scribbles.append(w)

        self._show_bubble(random.choice([
            "I drew something.", "Art.", "A contribution.",
            "Don't look at it.", "It means something.",
            "I was bored.", "Certified masterpiece.",
            "I did that.", "You're welcome.",
        ]))

    def _do_trip(self):
        """Multi-phase stumble: lurch → fall → sprawl → recover."""
        ox = int(self._physics.state.x)
        oy = int(self._physics.state.y)
        self._anim.set_state(State.DRAG, force=True)

                                             
        lurch_n = [0]
        lurch_t = QTimer(self)
        dir_sign = 1 if self._physics.state.walk_dir >= 0 else -1
        lurches  = [(dir_sign*14, -2), (-dir_sign*8, 3), (dir_sign*11, -1),
                    (-dir_sign*6, 2), (dir_sign*4, -1), (0, 0)]
        def do_lurch():
            i = lurch_n[0]
            if i >= len(lurches):
                lurch_t.stop(); lurch_t.deleteLater()
                                       
                self._physics.state.vy = -5.0
                self._physics.state.vx = dir_sign * 2.0
                self._physics.state.on_ground = False
                self._anim.set_state(State.FALL, force=True)
                self._sound.land()
                QTimer.singleShot(600, lambda: (
                    self._physics.state.__setattr__('x', float(ox)),
                    self._anim.set_state(State.IDLE, force=True)
                ))
                return
            dx, dy = lurches[i]
            self.move(ox+dx, oy+dy); lurch_n[0] += 1
        lurch_t.timeout.connect(do_lurch); lurch_t.start(45)

        self._show_bubble(random.choice([
            "That didn't happen.", "Intentional.", "I meant to do that.",
            "The floor moved.", "Traction issue.", "No witnesses.",
            "I tripped. On purpose.", "Unrelated to physics.",
        ]))

    def _do_stare_spot(self):
        """Walk toward a random spot, stop, stare at it, then walk away baffled."""
        tx = random.randint(self._screen.x + 50, self._screen.right - 100)

                                        
        s = self._physics.state
        going_right = tx > s.x
        self._drift_target_x = float(tx)
        self._drift_speed = 9.0 if going_right else -9.0
        s.walk_dir = 1 if going_right else -1

                                             
        def start_stare():
            self._drift_target_x = None
            self._drift_speed = 0.0
            self._anim.set_state(State.LOOK_AROUND, force=True)
            self._show_bubble(random.choice([
                "…", "Something over there.", "I see it.", "Don't look.",
                "It's nothing. Probably.", "I'm watching that pixel.",
                "There's something here.", "I'm not going to explain.",
            ]))
                                                                         
            QTimer.singleShot(random.randint(2000, 3500), walk_away)

        def walk_away():
            s2 = self._physics.state
            s2.walk_dir = -1 if going_right else 1
            self._anim.set_state(
                State.WALK_LEFT if going_right else State.WALK_RIGHT, force=True)

        QTimer.singleShot(1200, start_stare)

    def _do_freeze_glitch(self):
        """Freeze mid-stride, glitch-flicker, snap back confused."""
                                     
        self._anim.set_state(State.IDLE, force=True)
        ox, oy = self.x(), self.y()
        dur = random.randint(1000, 2200)

                                                                   
        def do_flicker():
            flick_n = [0]
            flick_t = QTimer(self)
            def flick():
                flick_n[0] += 1
                if flick_n[0] > 6:
                    flick_t.stop(); flick_t.deleteLater()
                    self.move(ox, oy)
                    self._show_bubble(random.choice([
                        "Sorry. Was somewhere else.",
                        "Brief technical difficulty. Emotional in nature.",
                        "I'm back. Where was I.",
                        "That was a moment of absence. I'm fine.",
                        "I needed a second. Had it. Moving on.",
                        "Error. Just kidding. Kind of.",
                    ]))
                    self._anim.set_state(State.IDLE, force=True)
                    return
                             
                self.move(ox + random.randint(-2,2), oy + random.randint(-2,2))
            flick_t.timeout.connect(flick); flick_t.start(55)

        QTimer.singleShot(dur, do_flicker)

    def _do_poem(self):
        """Show a short bad poem about the current app."""
        cat = self._gremlin._last_category
        poem = self._gremlin.get_poem_for_category(cat)
                                       
        lines = poem.split('\n')
        for i, line in enumerate(lines):
            QTimer.singleShot(i * 1200, lambda l=line: self._show_bubble(l, duration_ms=1400))

    def _do_letter(self):
        """Read out a mysterious letter line by line."""
        sequence = self._gremlin.get_letter_sequence()
        self._anim.set_state(State.IDLE, force=True)
        for i, line in enumerate(sequence):
            QTimer.singleShot(i * 1800, lambda l=line: self._show_bubble(l, duration_ms=2000))
        QTimer.singleShot(len(sequence) * 1800 + 500,
                          lambda: self._anim.set_state(State.IDLE, force=True))

    def _do_window_catch(self):
        """React dramatically to a window being minimised."""
        self._anim.set_state(State.FLY, force=True)
        self._show_bubble(random.choice([
            "I'll catch it.", "Coming!", "On it.",
            "Gone.", "It's gone.", "I almost had it.",
        ]))

                                           

    def _on_anim_state_change(self, new_state: "State") -> None:
        """Called by AnimationController whenever state changes."""
                     
        if new_state == State.FALL:   self._sound.bounce()
        elif new_state == State.DRAG: self._sound.drag_squeak()
        elif new_state == State.SLEEP: self._sound.sleep_tone()
        if not self._chaos_mode:
            return
        if new_state == State.SLEEP:
            QTimer.singleShot(400, lambda: self._show_bubble(
                random.choice(["Zzzzzzz…..", "zZzZzZz…", "💤 zzz…", "Zzz… (finally some peace)",
                               "zzzzzz", "Zzz… don't wake me", "z z z z z"]),
                duration_ms=3500,
            ))

    def _show_bubble(self, text: str, duration_ms: int = 4500):
        if self._quiet_mode: return
        self._sound.bubble_pop()
        b = DialogueBubble(text, self._screen, duration_ms)
        live = [x for x in self._active_bubbles if x.is_alive()]
        stack_idx = len(live)
        b.reposition(self.x(), self.y(), self.width(), self.height(),
                     self._anim.state, stack_index=stack_idx)
        self._active_bubbles = live + [b]

    # ------------------------------------------------------------------
    # Dialog + decision system
    # ------------------------------------------------------------------
    # Rules enforced here:
    #   * Only ONE interactive dialog visible at a time (checked via
    #     _interactive_bubble.is_alive()).
    #   * Per-state cooldown is enforced by PetStateMachine.dialog_ready()
    #     so the player is never spammed with popups.
    #   * The dialog widget is non-blocking: it runs on the Qt event loop
    #     and auto-dismisses after a timeout.

    def _trigger_interactive_dialog(self) -> None:
        if self._quiet_mode:
            return
        if self._interactive_bubble and self._interactive_bubble.is_alive():
            return
        if not self._pet_state.dialog_ready():
            return
        dialog = self._dialog_system.pick()
        bubble = InteractiveBubble(dialog, self._screen, self._on_dialog_choice)
        bubble.reposition(self.x(), self.y(), self.width(), self.height())
        self._interactive_bubble = bubble
        self._pet_state.note_dialog_shown()

    def _on_dialog_choice(self, result: str) -> None:
        new_state = DialogSystem.result_to_state(result)
        self._pet_state.set(new_state)
        self._show_bubble(DialogSystem.reaction(result), duration_ms=3000)
        self._apply_state_behavior()

    # ------------------------------------------------------------------
    # Behavior reactions driven purely by PetState
    # ------------------------------------------------------------------
    # Called whenever the state changes. Does not loop, does not recurse.
    # All visual effects are queued on the existing QTimer-driven loop.

    def _apply_state_behavior(self) -> None:
        st = self._pet_state.state
        self._physics.state.vx = 0.0  # reset any drift from previous state
        if st is PetState.HAPPY:
            self._anim.set_state(State.WAVE, force=True)
        elif st is PetState.ANGRY:
            self._do_chaos_action("shake")
        elif st is PetState.SATISFIED:
            self._anim.set_state(State.STRETCH, force=True)
        # IDLE: just let the animation state machine pick its next variant.

    def _update_sprite(self):
        img = self._anim.current_image
        pixmap = pil_to_qpixmap(img)
        self._label.setPixmap(pixmap); self._label.resize(pixmap.size()); self.resize(pixmap.size())
        self._physics.set_sprite_size(pixmap.width(), pixmap.height())
                                                      
        if self._anim.state in (State.CLIMB_RIGHT, State.CLIMB_LEFT):
            try:
                from sprite_loader import get_climb_canvas_size
                ccw, _ = get_climb_canvas_size(self._anims)
                self._physics.set_climb_canvas_w(ccw)
            except Exception:
                pass
        try:
            mask = make_mask_from_pixmap(pixmap); self.setMask(QRegion(mask))
        except Exception: pass

    def mousePressEvent(self, event):
        btn = event.button()
        left_btn  = Qt.MouseButton.LeftButton  if _QT6 else Qt.LeftButton
        right_btn = Qt.MouseButton.RightButton if _QT6 else Qt.RightButton
        if btn == left_btn:
            self._dragging = True
            self._drag_offset = event.position().toPoint() if _QT6 else event.pos()
            self._anim.begin_drag()
            self._physics.state.on_ground = False; self._physics.state.climbing = False
            if self._chaos_mode and random.random() < 0.55:
                self._show_bubble(random.choice(__import__("chaos_gremlin").DRAG_LINES))
        elif btn == right_btn:
            gp = event.globalPosition().toPoint() if _QT6 else event.globalPos()
            self._app_ref.show_context_menu(self, gp)

    def mouseMoveEvent(self, event):
        if self._dragging:
            pos = event.globalPosition().toPoint() if _QT6 else event.globalPos()
            new_pos = pos - self._drag_offset; self.move(new_pos)
            dx = new_pos.x() - self._physics.state.x
            dy = new_pos.y() - self._physics.state.y
            self._physics.apply_drag_move(dx, dy); self._update_sprite()

    def mouseReleaseEvent(self, event):
        left_btn = Qt.MouseButton.LeftButton if _QT6 else Qt.LeftButton
        if event.button() == left_btn and self._dragging:
            self._dragging = False; self._anim.end_drag()
            self._sound.release_drop()
            self._physics.state.on_ground = False
            if self._chaos_mode and random.random() < 0.45:
                self._show_bubble(random.choice(__import__("chaos_gremlin").RELEASE_LINES))

    def mouseDoubleClickEvent(self, event):
        self._anim.set_state(State.FLY, force=True)
        if self._chaos_mode:
            self._show_bubble(random.choice(["Up here.", "Briefly airborne.", "Gravity is advisory.", "I can see your tabs from here.", "Nice view. Still judging you."]))

    def set_behavior_mode(self, mode: str):
        self._cfg["behavior_mode"] = mode
        self._anim.set_behavior_mode(mode); self._physics.set_behavior_mode(mode)

    def set_animation_speed(self, speed: float):
        self._cfg["animation_speed"] = speed; self._anim.speed = speed

    def react_to_cpu(self, pct: float):
        threshold = self._cfg.get("cpu_high_threshold", 85)
        if pct >= threshold and not self._cpu_tired:
            self._cpu_tired = True
            self._anim.set_state(State.SLEEP, force=True)
            if self._chaos_mode:
                self._gremlin.notify_cpu(pct)
                for ev in self._gremlin.consume_events():
                    if ev.kind == "dialogue": self._show_bubble(ev.text)
        elif pct < threshold - 10 and self._cpu_tired:
            self._cpu_tired = False; self._anim.set_state(State.IDLE, force=True)

    def show_dialogue(self, text: str):
        self._show_bubble(text)

    def close_konqi(self):
        self._timer.stop()
        if hasattr(self, "_gremlin_timer"): self._gremlin_timer.stop()
        for b in self._active_bubbles:
            try: b._dismiss() if b.is_alive() else None
            except Exception: pass
        self.close()

                                                                             
          
                                                                             
class KonqiApp(QApplication):
    def __init__(self, argv, config):
        super().__init__(argv)
        self.setApplicationName("Konqi Shimeji")
        self.setApplicationDisplayName("Konqi – Chaos Gremlin Edition")
        self.setQuitOnLastWindowClosed(False)
        self._cfg = config
        self._konqis: List[KonqiWindow] = []
        self._anims = None
        self._gremlin = GremlinBrain()
        self.dialog_system = DialogSystem()
        self.pet_state     = PetStateMachine()
        self._loading_label = None
        self._show_loading()
        self._loader = SpriteLoaderThread(force=False)
        self._loader.done.connect(self._on_sprites_loaded)
        self._loader.start()
        self._cpu_monitor = None
        if config.get("cpu_reactions") and _PSUTIL:
            self._cpu_monitor = CPUMonitor(interval=5.0)
            self._cpu_monitor.cpu_level.connect(self._on_cpu_level)
            self._cpu_monitor.start()
        self._sound_engine = SoundEngine(enabled=config.get('sound_effects', False))
        self._tray = None; self._setup_tray()
                                            
        self._key_count: int = 0
        self._key_timer: float = time.time()
        self.installEventFilter(self)
        if config.get('chaos_mode', True):
            self.start_notification_watcher()

    def _show_loading(self):
        w = QWidget()
        w.setWindowTitle("Konqi Shimeji")
        w.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        w.setStyleSheet("background-color:#1a0a2e;color:#FFD93D;border-radius:12px;"
                        "padding:16px;border:2px solid #CC5DE8;")
        layout = QVBoxLayout(w)
        lbl = QLabel("🐉  Summoning the Chaos Gremlin…\n\nPreparing sarcastic commentary…\n"
                     "Loading questionable advice database…")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size:13px;padding:20px;color:#FF6B6B;")
        layout.addWidget(lbl); w.resize(420, 130)
        center = QApplication.primaryScreen().geometry().center()
        w.move(center.x()-210, center.y()-65); w.show()
        self._loading_label = w

    @pyqtSlot(dict)
    def _on_sprites_loaded(self, animations):
        if self._loading_label: self._loading_label.close(); self._loading_label = None
        self._anims = animations
        for _ in range(max(1, self._cfg.get("spawn_count", 1))):
            self.spawn_konqi()

    def spawn_konqi(self):
        if self._anims is None or len(self._konqis) >= 10: return
        screens = self.screens()
        screen = (random.choice(screens) if self._cfg.get("multi_monitor") and len(screens)>1
                  else self.primaryScreen())
        screen_rect = get_screen_rect_qt(screen)
        k = KonqiWindow(self._anims, screen_rect, dict(self._cfg), self, self._gremlin)
        self._konqis.append(k)
        log.info("Spawned Konqi #%d", len(self._konqis))
        if self._cfg.get("chaos_mode", True):
            greeting = random.choice(__import__("chaos_gremlin").SPAWN_GREETINGS)
            QTimer.singleShot(2000, lambda: k.show_dialogue(greeting))

    def summon_twin(self, caller: "KonqiWindow") -> None:
        """Spawn a temporary second Konqi that argues with the caller, then leaves."""
        if len(self._konqis) >= 10: return
        self.spawn_konqi()
        twin = self._konqis[-1]
        from chaos_gremlin import TWIN_LINES_A, TWIN_LINES_B
                                    
        def argue():
            if caller.is_visible() if hasattr(caller,'is_visible') else True:
                caller._show_bubble(random.choice(TWIN_LINES_A))
            QTimer.singleShot(1800, lambda: twin.show_dialogue(random.choice(TWIN_LINES_B)) if twin in self._konqis else None)
            QTimer.singleShot(3600, lambda: caller._show_bubble(random.choice(TWIN_LINES_A)) if caller in self._konqis else None)
            QTimer.singleShot(5400, lambda: self.remove_konqi(twin) if twin in self._konqis else None)
        self._sound_engine.twin_discord()
        self._gremlin.notify_clone_spawned(len(self._konqis))
        QTimer.singleShot(500, argue)

    def start_notification_watcher(self) -> None:
        """Watch for dbus desktop notifications and react."""
        try:
            self._notif_proc = subprocess.Popen(
                ["dbus-monitor", "--session",
                 "interface='org.freedesktop.Notifications',member='Notify'"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1
            )
            self._notif_timer = QTimer(self)
            self._notif_timer.setInterval(500)
            self._notif_timer.timeout.connect(self._check_notifications)
            self._notif_timer.start()
            log.info("Notification watcher started")
        except Exception as exc:
            log.debug("Notification watcher failed: %s", exc)

    def _check_notifications(self) -> None:
        if not hasattr(self, '_notif_proc') or self._notif_proc is None:
            return
        try:
            ready, _, _ = select.select([self._notif_proc.stdout], [], [], 0)
            if not ready:
                return
            line = self._notif_proc.stdout.readline()
            if line and 'Notify' in line:
                self._gremlin.notify_system_notification()
                events = self._gremlin.consume_events()
                for k in self._konqis:
                    for ev in events:
                        if ev.kind == "dialogue":
                            k.show_dialogue(ev.text)
                            break
        except Exception:
            pass

    def remove_konqi(self, k):
        if k in self._konqis: self._konqis.remove(k)
        k.close_konqi()

    def show_context_menu(self, konqi, pos):
        menu = QMenu()
        STYLE = """QMenu{background:#1a0a2e;color:#FFD93D;border:1px solid #CC5DE8;
                   border-radius:8px;padding:4px;font-size:13px;}
                   QMenu::item{padding:6px 20px;border-radius:4px;}
                   QMenu::item:selected{background:#2D1B4E;}
                   QMenu::separator{height:1px;background:#CC5DE8;margin:4px;}"""
        menu.setStyleSheet(STYLE)

        def act(label, fn): a = QAction(label, menu); a.triggered.connect(fn); menu.addAction(a); return a

        act("🐉  Spawn new Konqi", self.spawn_konqi)
        act("✕   Remove this Konqi", lambda: self.remove_konqi(konqi))
        menu.addSeparator()

        chaos_lbl = "🔇  Disable Chaos Mode" if self._cfg.get("chaos_mode",True) else "🔊  Enable Chaos Mode"
        act(chaos_lbl, self._toggle_chaos)
        quiet_lbl = "💬  Enable Dialogue" if self._cfg.get("quiet_mode",False) else "🤫  Quiet Mode (No Bubbles)"
        act(quiet_lbl, self._toggle_quiet)
        sound_lbl = "🔇  Disable Sound Effects" if self._cfg.get("sound_effects",False) else "🔊  Enable Sound Effects"
        act(sound_lbl, self._toggle_sound)
        menu.addSeparator()

        act("💡  Give me a useless PC tip", lambda: self._force_tip(konqi))
        act("🔥  Hardware roast me again",   lambda: self._force_hw_roast(konqi))
        menu.addSeparator()

        mode_menu = menu.addMenu("⚡  Behavior Mode"); mode_menu.setStyleSheet(STYLE)
        for mn, ml in [("calm","😴 Calm"),("hyper","⚡ Hyper")]:
            a = QAction(ml, mode_menu); a.setCheckable(True)
            a.setChecked(self._cfg["behavior_mode"]==mn)
            a.triggered.connect(lambda checked,m=mn: self._set_behavior_mode(m))
            mode_menu.addAction(a)

        speed_menu = menu.addMenu("🎬  Animation Speed"); speed_menu.setStyleSheet(STYLE)
        for sl, sv in [("0.5×",0.5),("1×",1.0),("1.5×",1.5),("2×",2.0)]:
            a = QAction(sl, speed_menu); a.setCheckable(True)
            a.setChecked(abs(self._cfg["animation_speed"]-sv)<0.01)
            a.triggered.connect(lambda checked,s=sv: self._set_speed(s))
            speed_menu.addAction(a)

        force_menu = menu.addMenu("🎭  Play Animation"); force_menu.setStyleSheet(STYLE)
        for st, lbl in [(State.SLEEP,"💤 Sleep"),(State.FLY,"🦅 Fly"),
                         (State.STRETCH,"🙆 Stretch"),(State.IDLE,"🧍 Idle")]:
            a = QAction(lbl, force_menu)
            a.triggered.connect(lambda checked,s=st,k=konqi: k._anim.set_state(s,force=True))
            force_menu.addAction(a)

        chaos_menu = menu.addMenu("💥  Chaos Actions"); chaos_menu.setStyleSheet(STYLE)
        for an, al in [("teleport","⚡ Teleport"),("spin","🌀 Spin"),("drift","💨 Drift"),
                        ("shake","🫨 Shake"),("dive","🚀 Dive"),("bounce","🏀 Bounce"),
                        ("trip","🤸 Trip"),("stare_spot","👁 Stare"),
                        ("freeze_glitch","💀 Glitch"),("poem","📜 Poem"),("letter","✉ Letter")]:
            a = QAction(al, chaos_menu)
            a.triggered.connect(lambda checked,x=an,k=konqi: k._do_chaos_action(x))
            chaos_menu.addAction(a)

        menu.addSeparator()
        autostart_lbl = "Disable Autostart" if autostart_is_enabled() else "Enable Autostart on Boot"
        act(autostart_lbl, self._toggle_autostart)
        if _PSUTIL:
            cpu_lbl = "🧠 Disable CPU Reactions" if self._cfg.get("cpu_reactions") else "🧠 Enable CPU Reactions"
            act(cpu_lbl, self._toggle_cpu_reactions)
        menu.addSeparator()
        a = QAction(f"📊  Active Konqis: {len(self._konqis)}", menu); a.setEnabled(False); menu.addAction(a)
        menu.addSeparator()
        act("🚪  Exit", self.quit_app)
        menu.exec(pos)

    def _toggle_chaos(self):
        self._cfg["chaos_mode"] = not self._cfg.get("chaos_mode", True); save_config(self._cfg)
        for k in self._konqis: k._chaos_mode = self._cfg["chaos_mode"]

    def _toggle_sound(self):
        self._cfg['sound_effects'] = not self._cfg.get('sound_effects', False)
        save_config(self._cfg)
        self._sound_engine.enabled = self._cfg['sound_effects']
        for k in self._konqis: k._sound.enabled = self._cfg['sound_effects']

    def _toggle_quiet(self):
        self._cfg["quiet_mode"] = not self._cfg.get("quiet_mode", False); save_config(self._cfg)
        for k in self._konqis: k._quiet_mode = self._cfg["quiet_mode"]

    def _force_tip(self, konqi):
        from chaos_gremlin import USELESS_TIPS; konqi.show_dialogue(random.choice(USELESS_TIPS))

    def _force_hw_roast(self, konqi):
        from chaos_gremlin import POTATO_ROASTS, BEAST_PC_JEALOUSY
        tier = self._gremlin._hw_tier
        if tier=="potato": konqi.show_dialogue(random.choice(POTATO_ROASTS))
        elif tier=="beast": konqi.show_dialogue(random.choice(BEAST_PC_JEALOUSY))
        else: konqi.show_dialogue(random.choice([
            "Middling specs. The safe, beige choice. No ambitions.",
            "16GB RAM. The 'I looked at benchmarks once' build.",
            "Your specs are exactly average. Statistically unremarkable.",
            "Not a potato, not a beast. Just... there. Existing.",
        ]))

    def _set_behavior_mode(self, mode):
        self._cfg["behavior_mode"] = mode
        for k in self._konqis: k.set_behavior_mode(mode)
        save_config(self._cfg)

    def _set_speed(self, speed):
        self._cfg["animation_speed"] = speed
        for k in self._konqis: k.set_animation_speed(speed)
        save_config(self._cfg)

    def _toggle_autostart(self):
        if autostart_is_enabled(): autostart_disable(); msg="Autostart disabled."
        else: autostart_enable(); msg="Konqi will haunt you on every login. Sleep well."
        if self._tray and self._tray.supportsMessages():
            self._tray.showMessage("Konqi Shimeji", msg,
                QSystemTrayIcon.MessageIcon.Information if _QT6 else QSystemTrayIcon.Information, 3000)

    def _toggle_cpu_reactions(self):
        self._cfg["cpu_reactions"] = not self._cfg.get("cpu_reactions", True); save_config(self._cfg)

    @pyqtSlot(float)
    def _on_cpu_level(self, pct):
        for k in self._konqis: k.react_to_cpu(pct)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon if _QT6 else self.style().SP_ComputerIcon))
        self._tray.setToolTip("Konqi Shimeji – Chaos Gremlin Edition")
        tm = QMenu()
        tm.setStyleSheet("QMenu{background:#1a0a2e;color:#FFD93D;border:1px solid #CC5DE8;}"
                         "QMenu::item{padding:5px 16px;}QMenu::item:selected{background:#2D1B4E;}")
        a1=QAction("🐉 Spawn Konqi",tm); a1.triggered.connect(self.spawn_konqi); tm.addAction(a1)
        a2=QAction("🚪 Exit",tm); a2.triggered.connect(self.quit_app); tm.addAction(a2)
        self._tray.setContextMenu(tm)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _tray_activated(self, reason):
        double = QSystemTrayIcon.ActivationReason.DoubleClick if _QT6 else QSystemTrayIcon.DoubleClick
        if reason == double: self.spawn_konqi()

    def eventFilter(self, obj, event):
        try:
            from PyQt6.QtCore import QEvent
            KEY_PRESS = QEvent.Type.KeyPress
        except ImportError:
            from PyQt5.QtCore import QEvent
            KEY_PRESS = QEvent.KeyPress
        if event.type() == KEY_PRESS:
            self._key_count += 1
            now = time.time()
            dt = now - self._key_timer
            if dt >= 2.0:
                self._gremlin.notify_typing(self._key_count, dt)
                self._key_count = 0
                self._key_timer = now
        return False                       

    def quit_app(self):
        try:
            last_line = None
            if self._konqis:

                bubbles = [b for b in self._konqis[0]._active_bubbles if b.is_alive()]
                if bubbles: last_line = bubbles[-1]._text
            self._gremlin.save_session_memory(last_line=last_line)
        except Exception: pass
        try:
            if hasattr(self, '_notif_timer') and self._notif_timer:
                self._notif_timer.stop()
            if hasattr(self, '_notif_proc') and self._notif_proc:
                self._notif_proc.terminate()
                self._notif_proc = None
        except Exception: pass
        if self._cpu_monitor: self._cpu_monitor.stop()
        for k in list(self._konqis): k.close_konqi()
        self._konqis.clear()
        if self._tray: self._tray.hide()
        self.quit()

def main():
    parser = argparse.ArgumentParser(description="Konqi Shimeji – Chaos Gremlin Edition")
    parser.add_argument("--debug",          action="store_true")
    parser.add_argument("--hyper",          action="store_true")
    parser.add_argument("--count",          type=int, default=None)
    parser.add_argument("--reload-sprites", action="store_true")
    parser.add_argument("--quiet",          action="store_true", help="Disable dialogue bubbles")
    parser.add_argument("--no-chaos",       action="store_true", help="Disable chaos gremlin brain")
    args = parser.parse_args()

    if args.debug: logging.getLogger().setLevel(logging.DEBUG)

    cfg = load_config()
    if args.hyper:    cfg["behavior_mode"] = "hyper"
    if args.count:    cfg["spawn_count"]   = max(1, args.count)
    if args.quiet:    cfg["quiet_mode"]    = True
    if args.no_chaos: cfg["chaos_mode"]    = False

    if sys.platform.startswith("linux") and "WAYLAND_DISPLAY" in os.environ:
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    if _QT6:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = KonqiApp(sys.argv, cfg)

    if args.reload_sprites:
        app._loader.quit(); app._loader.wait()
        app._loader = SpriteLoaderThread(force=True)
        app._loader.done.connect(app._on_sprites_loaded)
        app._loader.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
