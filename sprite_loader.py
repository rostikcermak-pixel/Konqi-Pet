"""
sprite_loader.py – Multi-sprite animation generator for Konqi Shimeji.

Per-state sprites:
  walk_right / walk_left   → konqi_walk.png
  idle / look_around / wave → konqi_idle.png
  sleep                    → konqi_sleep.png
  climb_right / climb_left → konqi_climb.png  (left flips base first)
  fall                     → konqi_walk.png
  drag                     → konqi_idle.png
  fly                      → konqi_idle.png
  stretch                  → konqi_idle.png
"""

from __future__ import annotations

import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance

log = logging.getLogger(__name__)

ASSETS_DIR    = Path(__file__).parent / "assets"
FRAMES_DIR    = ASSETS_DIR / "frames"
SPRITE_HEIGHT = 96

SPRITE_FILES = {
    "walk":  "konqi_walk.png",
    "climb": "konqi_climb.png",
    "sleep": "konqi_sleep.png",
    "idle":  "konqi_idle.png",
    "base":  "konqi_base.png",
}

                                                                             
         
                                                                             

def _make_canvas(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))

def _load_sprite(assets_dir: Path, key: str) -> Image.Image:
    fname = SPRITE_FILES.get(key, SPRITE_FILES["base"])
    path  = assets_dir / fname
    if not path.exists():
        path = assets_dir / SPRITE_FILES["base"]
    if not path.exists():
        raise FileNotFoundError(f"No sprite found at {path}.")
    img  = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    ratio = SPRITE_HEIGHT / img.height
    return img.resize((max(1, int(img.width * ratio)), SPRITE_HEIGHT), Image.LANCZOS)

                                                                             
                  
                                                                             

def gen_walk_frames(base: Image.Image, n: int = 12) -> List[Image.Image]:
    """Walk right: stride bob + lean + landing squash. walk_left = flip."""
    w, h = base.size
    canvas_h = h + 16
    frames = []
    for i in range(n):
        t    = i / n
        bob  = int(6 * abs(math.sin(t * math.pi * 2)))
        lean = int(4 * math.sin(t * math.pi * 2))
        sy   = 1.0 - 0.05 * abs(math.sin(t * math.pi * 2))
        nh2  = max(1, int(h * sy))
        frame = base.resize((w, nh2), Image.LANCZOS)
        c = _make_canvas(w + 12, canvas_h)
        c.paste(frame, (3 + lean, canvas_h - nh2 - bob), frame)
        frames.append(c)
    return frames

def gen_idle_frames(base: Image.Image, n: int = 12) -> List[Image.Image]:
    """Breathing pulse + sway with occasional head-tilt on the beat."""
    w, h = base.size
    frames = []
    for i in range(n):
        t      = i / n
        breath = 1.0 + 0.030 * math.sin(t * math.pi * 2)
        sway   = 1.8 * math.sin(t * math.pi * 2)
        tilt   = 3.5 * math.sin(t * math.pi * 4) if i >= n // 2 else 0.0
        nw2    = max(1, int(w * breath))
        nh2    = max(1, int(h * breath))
        resized = base.resize((nw2, nh2), Image.LANCZOS)
        frame   = resized.rotate(sway + tilt, expand=False, resample=Image.BICUBIC)
        c = _make_canvas(w + 8, h + 8)
        c.paste(frame, ((w + 8 - nw2) // 2, (h + 8 - nh2)), frame)
        frames.append(c)
    return frames

def gen_look_around_frames(base: Image.Image, n: int = 14) -> List[Image.Image]:
    """Head-turn left then right: horizontal squish + slight bob at peak."""
    w, h = base.size
    frames = []
    for i in range(n):
        t   = i / n
        sx  = 1.0 - 0.45 * abs(math.sin(t * math.pi * 2))
        bob = int(3 * abs(math.sin(t * math.pi * 2)))
        nw2 = max(1, int(w * sx))
        f   = base.resize((nw2, h), Image.LANCZOS)
        c   = _make_canvas(w + 8, h + 6)
        c.paste(f, ((w + 8 - nw2) // 2, 2 + bob), f)
        frames.append(c)
    return frames

def gen_wave_frames(base: Image.Image, n: int = 14) -> List[Image.Image]:
    """Excited wave: big tilt, high hop, pulse scale — clearly celebrating."""
    w, h = base.size
    frames = []
    for i in range(n):
        t     = i / n
        tilt  = 12 * math.sin(t * math.pi * 2)
        bob   = int(10 * abs(math.sin(t * math.pi * 2)))
        pulse = 1.0 + 0.06 * abs(math.sin(t * math.pi * 2))
        nw2   = max(1, int(w * pulse))
        nh2   = max(1, int(h * pulse))
        resized = base.resize((nw2, nh2), Image.LANCZOS)
        f     = resized.rotate(tilt, expand=False, resample=Image.BICUBIC)
        c     = _make_canvas(w + 12, h + 14)
        ox    = (w + 12 - f.width) // 2
        oy    = h + 14 - f.height - bob
        c.paste(f, (ox, oy), f)
        frames.append(c)
    return frames

def gen_sleep_frames(base: Image.Image, n: int = 8) -> List[Image.Image]:
    """Gentle breathing — nose bubble is baked into the sprite."""
    w, h = base.size
    cw, ch = w + 20, h + 16
    frames = []
    for i in range(n):
        t    = i / n
        sy   = 1.0 + 0.022 * math.sin(t * math.pi * 2)
        nh2  = max(1, int(h * sy))
        resized = base.resize((w, nh2), Image.LANCZOS)
        sway    = 0.4 * math.sin(t * math.pi * 2)
        frame   = resized.rotate(sway, expand=False, resample=Image.BICUBIC)
        c = _make_canvas(cw, ch)
        c.paste(frame, (2, ch - nh2), frame)
        frames.append(c)
    return frames

def gen_climb_frames(base: Image.Image, n: int = 8,
                     direction: str = "right") -> Tuple[List[Image.Image], int, int]:
    """
    Fixed-canvas climbing animation.

    Fixes vs old version:
    - climb_left now FLIPS the base first so Konqi faces inward (toward screen centre)
    - Canvas sized to actual sprite content bbox — eliminates the ~17px float gap
    - Physics X-pin uses canvas_w which now correctly hugs the wall

    Returns (frames, canvas_w, canvas_h).
    """
    sign = 1 if direction == "right" else -1
    LEAN = 22

                             
                                                                                
                                                                            
    if direction == "right":
        base = base.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    leaned = base.rotate(-sign * LEAN, expand=True, resample=Image.BICUBIC)
    lw, lh = leaned.size

                                                                
    bbox = leaned.getbbox() or (0, 0, lw, lh)
    cl, ct, cr, cb = bbox
    content_w = cr - cl
    content_h = cb - ct

    MAX_BOB = 6
    PAD     = 2                                      
    CANVAS_W = content_w + PAD * 2
    CANVAS_H = content_h + MAX_BOB + PAD * 2

    frames = []
    for i in range(n):
        t    = i / n
        bob  = int(MAX_BOB * abs(math.sin(t * math.pi * 2)))
        push = int(2 * abs(math.sin(t * math.pi * 2)))
        sy   = 1.0 + 0.03 * math.sin(t * math.pi * 2)
        nh2  = max(1, int(lh * sy))
        fs   = leaned.resize((lw, nh2), Image.LANCZOS)
        fb   = fs.getbbox() or (0, 0, lw, nh2)
        fc_l, fc_t, fc_r, fc_b = fb
        fc_w = fc_r - fc_l
        fc_h = fc_b - fc_t

        c = _make_canvas(CANVAS_W, CANVAS_H)
        if direction == "right":
            ox = CANVAS_W - PAD - fc_w - fc_l - push
        else:
            ox = PAD - fc_l + push
        oy = CANVAS_H - PAD - fc_h - fc_t - bob
        c.paste(fs, (ox, oy), fs)
        frames.append(c)

    return frames, CANVAS_W, CANVAS_H

def gen_fall_frames(base: Image.Image, n: int = 6) -> List[Image.Image]:
    """Progressive stretch + rotation as Konqi falls."""
    w, h = base.size
    frames = []
    for i in range(n):
        t   = i / n
        sy  = 1.0 + 0.10 * t
        sx  = 1.0 - 0.06 * t
        nw2 = max(1, int(w * sx))
        nh2 = max(1, int(h * sy))
        frame = base.resize((nw2, nh2), Image.LANCZOS)
        angle = 8 * math.sin(t * math.pi * 1.5)
        frame = frame.rotate(angle, expand=False, resample=Image.BICUBIC)
        frames.append(frame)
    return frames

def gen_drag_frames(base: Image.Image, n: int = 6) -> List[Image.Image]:
    """Wide panic wobble + brightness flash."""
    frames = []
    for i in range(n):
        t     = i / n
        angle = 16 * math.sin(i * math.pi * 2 / n)
        w, h  = base.size
        scale = 1.0 + 0.05 * abs(math.sin(i * math.pi / n))
        nw2   = max(1, int(w * scale))
        nh2   = max(1, int(h * scale))
        frame = base.resize((nw2, nh2), Image.LANCZOS)
        frame = frame.rotate(angle, expand=False, resample=Image.BICUBIC)
        frame = ImageEnhance.Brightness(frame).enhance(1.12)
        frames.append(frame)
    return frames

def gen_fly_frames(base: Image.Image, n: int = 8) -> List[Image.Image]:
    """Idle sprite bobs and tilts on a smooth arc."""
    w, h = base.size
    frames = []
    for i in range(n):
        t     = i / n
        dy    = int(7 * math.sin(t * math.pi * 2))
        tilt  = 9 * math.sin(t * math.pi * 2)
        scale = 1.0 + 0.02 * math.sin(t * math.pi * 2)
        nw2   = max(1, int(w * scale))
        nh2   = max(1, int(h * scale))
        resized = base.resize((nw2, nh2), Image.LANCZOS)
        frame   = resized.rotate(tilt, expand=False, resample=Image.BICUBIC)
        c = _make_canvas(w + 6, h + 16)
        c.paste(frame, ((w+6-frame.width)//2, 7+dy), frame)
        frames.append(c)
    return frames

def gen_stretch_frames(base: Image.Image, n: int = 12) -> List[Image.Image]:
    """Full squash-and-stretch yawn: wide squeeze, tall stretch, slow settle."""
    w, h = base.size
    frames = []
    for i in range(n):
        t = i / n
        if t < 0.20:
            p  = t / 0.20
            sy = 1.0 - 0.18 * p;  sx = 1.0 + 0.12 * p
        elif t < 0.40:
            p  = (t - 0.20) / 0.20
            sy = 0.82 + 0.18 * p; sx = 1.12 - 0.12 * p
        elif t < 0.65:
            p  = (t - 0.40) / 0.25
            sy = 1.0 + 0.26 * p;  sx = 1.0 - 0.10 * p
        elif t < 0.85:
            p  = (t - 0.65) / 0.20
            sy = 1.26 - 0.20 * p; sx = 0.90 + 0.08 * p
        else:
            p  = (t - 0.85) / 0.15
            sy = 1.06 - 0.06 * p; sx = 0.98 + 0.02 * p
        nw2 = max(1, int(w * sx))
        nh2 = max(1, int(h * sy))
        s   = base.resize((nw2, nh2), Image.LANCZOS)
        PAD_H = int(h * 0.28)
        c   = _make_canvas(w + 10, h + PAD_H)
        c.paste(s, ((c.width - nw2) // 2, c.height - nh2), s)
        frames.append(c)
    return frames

                                                                             
            
                                                                             

def _build_animations(assets_dir: Path) -> Dict[str, List[Image.Image]]:
    walk_s  = _load_sprite(assets_dir, "walk")
    idle_s  = _load_sprite(assets_dir, "idle")
    sleep_s = _load_sprite(assets_dir, "sleep")
    climb_s = _load_sprite(assets_dir, "climb")

    log.info("Sprites — walk:%s idle:%s sleep:%s climb:%s",
             walk_s.size, idle_s.size, sleep_s.size, climb_s.size)

                                                                                        
    walk_l_raw = gen_walk_frames(walk_s)
    walk_r = [f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in walk_l_raw]
    walk_l = walk_l_raw

    climb_r, ccw, cch = gen_climb_frames(climb_s, direction="right")
    climb_l, _,   _   = gen_climb_frames(climb_s, direction="left")

    return {
        "walk_right":   walk_r,
        "walk_left":    walk_l,
        "idle":         gen_idle_frames(idle_s),
        "look_around":  gen_look_around_frames(idle_s),
        "wave":         gen_wave_frames(idle_s),
        "sleep":        gen_sleep_frames(sleep_s),
        "climb_right":  climb_r,
        "climb_left":   climb_l,
        "fall":         gen_fall_frames(walk_s),
        "drag":         gen_drag_frames(idle_s),
        "fly":          gen_fly_frames(idle_s),
        "stretch":      gen_stretch_frames(idle_s),
        "_climb_size":  [Image.new("RGBA", (ccw, cch))],
    }

def _save_frames(animations: Dict[str, List[Image.Image]],
                 assets_dir: Path) -> None:
    frames_dir = assets_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    for name, frames in animations.items():
        anim_dir = frames_dir / name
        anim_dir.mkdir(exist_ok=True)
        for old in anim_dir.glob("*.png"):
            old.unlink(missing_ok=True)
        for idx, frame in enumerate(frames):
            frame.save(anim_dir / f"{idx:02d}.png", "PNG")

def load_sprites(assets_dir: Optional[Path] = None,
                 force_download: bool = False) -> Dict[str, List[Image.Image]]:
    if assets_dir is None:
        assets_dir = ASSETS_DIR
    assets_dir.mkdir(parents=True, exist_ok=True)

    custom = assets_dir / "custom" / "base.png"
    if custom.exists():
        try:
            base = Image.open(custom).convert("RGBA")
            bbox = base.getbbox()
            if bbox: base = base.crop(bbox)
            ratio = SPRITE_HEIGHT / base.height
            base  = base.resize((max(1,int(base.width*ratio)), SPRITE_HEIGHT), Image.LANCZOS)
            log.info("Custom sprite override: %s", custom)
            return _build_from_single(base, assets_dir)
        except Exception as exc:
            log.warning("Custom sprite unreadable (%s), using per-state sprites", exc)

    log.info("Building animations from per-state sprites…")
    animations = _build_animations(assets_dir)
    _save_frames(animations, assets_dir)
    return animations

def _build_from_single(base: Image.Image,
                       assets_dir: Path) -> Dict[str, List[Image.Image]]:
    walk_l_raw = gen_walk_frames(base)
    walk_r = [f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in walk_l_raw]
    walk_l = walk_l_raw
    climb_r, ccw, cch = gen_climb_frames(base, direction="right")
    climb_l, _, _     = gen_climb_frames(base, direction="left")
    anims = {
        "walk_right":   walk_r,
        "walk_left":    walk_l,
        "idle":         gen_idle_frames(base),
        "look_around":  gen_look_around_frames(base),
        "wave":         gen_wave_frames(base),
        "sleep":        gen_sleep_frames(base),
        "climb_right":  climb_r,
        "climb_left":   climb_l,
        "fall":         gen_fall_frames(base),
        "drag":         gen_drag_frames(base),
        "fly":          gen_fly_frames(base),
        "stretch":      gen_stretch_frames(base),
        "_climb_size":  [Image.new("RGBA", (ccw, cch))],
    }
    _save_frames(anims, assets_dir)
    return anims

def get_cached_animations(assets_dir: Optional[Path] = None
                          ) -> Optional[Dict[str, List[Image.Image]]]:
    if assets_dir is None:
        assets_dir = ASSETS_DIR
    frames_dir = assets_dir / "frames"
    if not frames_dir.exists():
        return None

    expected = ["walk_right", "walk_left", "idle", "look_around", "wave",
                "sleep", "climb_right", "climb_left", "fall", "drag", "fly", "stretch"]
    animations: Dict[str, List[Image.Image]] = {}
    for name in expected:
        anim_dir = frames_dir / name
        if not anim_dir.exists():
            return None
        pngs = sorted(anim_dir.glob("*.png"))
        if not pngs:
            return None
        animations[name] = [Image.open(p).convert("RGBA") for p in pngs]

    cache_mtime = min(
        (frames_dir / name / "00.png").stat().st_mtime
        for name in expected
        if (frames_dir / name / "00.png").exists()
    )
    for key in ("walk", "idle", "sleep", "climb", "base"):
        sp = assets_dir / SPRITE_FILES.get(key, "konqi_base.png")
        if sp.exists() and sp.stat().st_mtime > cache_mtime:
            log.info("Sprite %s newer than cache — regenerating", sp.name)
            return None

    cs_dir = frames_dir / "_climb_size"
    if cs_dir.exists():
        pngs = sorted(cs_dir.glob("*.png"))
        if pngs:
            animations["_climb_size"] = [Image.open(pngs[0]).convert("RGBA")]

    log.info("Loaded cached frames from %s", frames_dir)
    return animations

def get_climb_canvas_size(animations: Dict[str, List[Image.Image]]) -> Tuple[int, int]:
    if "_climb_size" in animations:
        return animations["_climb_size"][0].size
    if "climb_right" in animations and animations["climb_right"]:
        return animations["climb_right"][0].size
    return (96, 108)
