"""
physics.py – Physics engine for Konqi Shimeji.

Climb fix: X is pinned absolutely to the screen edge every tick,
using the fixed climb canvas width so the sprite never drifts or clips.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

try:
    from ewmh import EWMH
    _ewmh = EWMH()
    _EWMH_AVAILABLE = True
    log.info("python-ewmh available – window climbing enabled")
except Exception:
    _ewmh = None                                    
    _EWMH_AVAILABLE = False
    log.info("python-ewmh not available – climbing screen edges only")

                                                                             
           
                                                                             

GRAVITY          = 0.55
MAX_FALL_SPEED   = 18.0
WALK_SPEED       = 2.0
HYPER_WALK_SPEED = 4.0
CLIMB_SPEED      = 2.2                                                
BOUNCE_DAMPING   = 0.3

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def left(self) -> int:   return self.x
    @property
    def right(self) -> int:  return self.x + self.w
    @property
    def top(self) -> int:    return self.y
    @property
    def bottom(self) -> int: return self.y + self.h

    def contains_x(self, px: int) -> bool:
        return self.left <= px <= self.right

    def contains_y(self, py: int) -> bool:
        return self.top <= py <= self.bottom

@dataclass
class PhysicsState:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = True
    climbing: bool = False
    climb_edge_x: Optional[int] = None
    climb_dir: str = "right"
    walk_dir: int = 1
    sprite_w: int = 96
    sprite_h: int = 96
                                                             
    climb_canvas_w: int = 96
    behavior_mode: str = "calm"

class PhysicsEngine:
    """
    Per-Konqi physics controller.
    Coordinate system: top-left origin, Y increases downward.
    """

    def __init__(
        self,
        screen_rect: Rect,
        initial_x: float = 100.0,
        initial_y: float = 0.0,
    ) -> None:
        self._screen = screen_rect
        self.state   = PhysicsState(x=initial_x, y=initial_y)
        self._floor_y = screen_rect.bottom
        self._windows: List[Rect] = []
        self._window_refresh_counter = 0
        self._WINDOW_REFRESH_INTERVAL = 120
                                                                             
        self._climb_canvas_w: int = 96

                                                                        
                
                                                                        

    def set_sprite_size(self, w: int, h: int) -> None:
        self.state.sprite_w = w
        self.state.sprite_h = h

    def set_climb_canvas_w(self, w: int) -> None:
        """Set the fixed canvas width used for climb frames."""
        self._climb_canvas_w = w

    def set_behavior_mode(self, mode: str) -> None:
        self.state.behavior_mode = mode

    def set_walk_direction(self, direction: int) -> None:
        self.state.walk_dir = direction

    def teleport(self, x: float, y: float) -> None:
        self.state.x  = x
        self.state.y  = y
        self.state.vx = 0.0
        self.state.vy = 0.0

    def apply_drag_move(self, dx: float, dy: float) -> None:
        self.state.x += dx
        self.state.y += dy
        self.state.vx = dx * 0.6
        self.state.vy = dy * 0.6
        self.state.on_ground = False
        self.state.climbing  = False

    def update(self) -> Tuple[str, bool]:
        s = self.state

        self._window_refresh_counter += 1
        if self._window_refresh_counter >= self._WINDOW_REFRESH_INTERVAL:
            self._window_refresh_counter = 0
            self._refresh_windows()

        floor = self._compute_floor()
        self._floor_y = floor

        old_walk_dir = s.walk_dir

                                   
        if not s.on_ground and not s.climbing:
            s.vy = min(s.vy + GRAVITY, MAX_FALL_SPEED)
            s.y  += s.vy
            s.x  += s.vx
            s.vx *= 0.95

            if s.y + s.sprite_h >= floor:
                s.y = float(floor - s.sprite_h)
                s.vy = -abs(s.vy) * BOUNCE_DAMPING
                if abs(s.vy) < 1.0:
                    s.vy = 0.0
                    s.on_ground = True
                    s.vx = 0.0
                return ("fall", False)

            if s.y < self._screen.top:
                s.y = float(self._screen.top)
                s.vy = abs(s.vy) * BOUNCE_DAMPING

            self._clamp_to_screen_x()
            return ("fall", False)

                      
        if s.climbing:
            return self._update_climb()

                               
        return self._update_walk(old_walk_dir)

                                                                        
                      
                                                                        

    def _update_walk(self, old_dir: int) -> Tuple[str, bool]:
        s = self.state
        speed = HYPER_WALK_SPEED if s.behavior_mode == "hyper" else WALK_SPEED
        s.x += speed * s.walk_dir
        dir_changed = (s.walk_dir != old_dir)
        sw = s.sprite_w

        if s.x < self._screen.left:
            s.x = float(self._screen.left)
            if random.random() < 0.35:
                self._start_climb("left")
                return ("climb_left", True)
            s.walk_dir = 1
            dir_changed = True

        elif s.x + sw > self._screen.right:
            s.x = float(self._screen.right - sw)
            if random.random() < 0.35:
                self._start_climb("right")
                return ("climb_right", True)
            s.walk_dir = -1
            dir_changed = True

        floor = self._compute_floor()
        if abs(s.y + s.sprite_h - floor) > 2:
            s.on_ground = False
            s.vy = 0.5
            return ("fall", False)

        anim = "walk_right" if s.walk_dir > 0 else "walk_left"
        return (anim, dir_changed)

    def _update_climb(self) -> Tuple[str, bool]:
        s = self.state

                 
        s.y -= CLIMB_SPEED

                                                                         
                                                                             
        if s.climb_dir == "right":
            s.x = float(self._screen.right - self._climb_canvas_w)
        else:
            s.x = float(self._screen.left)

                                          
        if s.y <= self._screen.top + 5:
            s.climbing  = False
            s.on_ground = False
            s.vy = 0.2
            s.vx = WALK_SPEED * (-1 if s.climb_dir == "right" else 1)
            return ("fall", False)

        anim = "climb_right" if s.climb_dir == "right" else "climb_left"
        return (anim, False)

    def _start_climb(self, direction: str) -> None:
        s = self.state
        s.climbing = True
        s.on_ground = False
        s.vx = 0.0
        s.vy = 0.0
        s.climb_dir = direction
                                                           
        if direction == "right":
            s.x = float(self._screen.right - self._climb_canvas_w)
        else:
            s.x = float(self._screen.left)

    def _compute_floor(self) -> int:
        s = self.state
        best_floor = self._screen.bottom
        feet_x = int(s.x + s.sprite_w / 2)
        konqi_bottom = int(s.y + s.sprite_h)
        for win in self._windows:
            if win.contains_x(feet_x) and win.top >= konqi_bottom - 4:
                best_floor = min(best_floor, win.top)
        return best_floor

    def _clamp_to_screen_x(self) -> None:
        s = self.state
        if s.x < self._screen.left:
            s.x = float(self._screen.left)
            s.vx = abs(s.vx) * BOUNCE_DAMPING
        elif s.x + s.sprite_w > self._screen.right:
            s.x = float(self._screen.right - s.sprite_w)
            s.vx = -abs(s.vx) * BOUNCE_DAMPING

    def _refresh_windows(self) -> None:
        if not _EWMH_AVAILABLE:
            return
        try:
            windows = _ewmh.getClientList()
            rects: List[Rect] = []
            for win in windows:
                try:
                    geom  = win.get_geometry()
                    t_xy  = win.translate_coords(win.parent, 0, 0)
                    abs_x = t_xy.x if hasattr(t_xy, 'x') else 0
                    abs_y = t_xy.y if hasattr(t_xy, 'y') else 0
                    w = geom.width
                    h = geom.height
                    if w > 10 and h > 10:
                        rects.append(Rect(abs_x, abs_y, w, h))
                except Exception:
                    pass
            self._windows = rects
        except Exception as exc:
            log.debug("Window refresh failed: %s", exc)
            self._windows = []

                                                                             
           
                                                                             

def get_screen_rect_qt(screen) -> Rect:
    g = screen.availableGeometry()
    return Rect(g.x(), g.y(), g.width(), g.height())
