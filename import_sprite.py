                      
"""
import_sprite.py – Import a custom sprite into Konqi Shimeji.

Two modes
─────────
1. Single-image mode  (most common):
       python3 import_sprite.py my_sprite.png
   Copies your PNG as the new base sprite, clears the frame cache, and
   regenerates all 10 animation sets using the same Pillow transforms.

2. Folder mode  (bring your own frames):
       python3 import_sprite.py --folder my_sprites/
   Expects this layout inside the folder:
       my_sprites/
         walk_right/   01.png 02.png ...   (≥2 frames)
         walk_left/    01.png ...          (optional – mirrored from walk_right if absent)
         idle/         01.png ...          (≥1 frame)
         sleep/        01.png ...          (optional)
         climb_right/  01.png ...          (optional)
         climb_left/   01.png ...          (optional)
         fall/         01.png ...          (optional)
         drag/         01.png ...          (optional)
         fly/          01.png ...          (optional)
         stretch/      01.png ...          (optional)
   Missing optional sets are auto-generated from the first idle frame.
   All images must be RGBA PNGs with transparent backgrounds.

After import, restart main.py – it will use your sprites automatically.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

                                                                               
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import sprite_loader as _sl
from sprite_loader import (
    SPRITE_HEIGHT, ASSETS_DIR,
    _crop_to_content, _resize_to_height, _save_frames,
    gen_walk_frames, gen_idle_frames, gen_sleep_frames,
    gen_climb_frames, gen_fall_frames, gen_drag_frames,
    gen_fly_frames, gen_stretch_frames,
)

CUSTOM_DIR   = ASSETS_DIR / "custom"
CUSTOM_BASE  = CUSTOM_DIR / "base.png"
FRAMES_DIR   = ASSETS_DIR / "frames"

ANIM_NAMES = [
    "walk_right", "walk_left", "idle", "sleep",
    "climb_right", "climb_left", "fall", "drag", "fly", "stretch",
]

                                                                               

def _clear_cache() -> None:
    """Wipe generated frame cache so next launch re-generates."""
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
        print("  ✓ Cleared frame cache")


def _load_png(path: Path) -> Image.Image:
    try:
        img = Image.open(path).convert("RGBA")
    except Exception as exc:
        _die(f"Cannot open image '{path}': {exc}")
    return img


def _die(msg: str) -> None:
    print(f"\n❌  {msg}", file=sys.stderr)
    sys.exit(1)


def _print_contact_sheet(animations: Dict[str, List[Image.Image]],
                          out_path: Path) -> None:
    """Save a quick preview grid to out_path."""
    CELL_W, CELL_H, LABEL_H = 130, 140, 18
    COLS = 5
    ROWS = (len(ANIM_NAMES) + COLS - 1) // COLS
    W = COLS * CELL_W
    H = ROWS * (CELL_H + LABEL_H) + 10
    sheet = Image.new("RGBA", (W, H), (30, 30, 46, 255))
    draw  = ImageDraw.Draw(sheet)

    for i, name in enumerate(ANIM_NAMES):
        col = i % COLS
        row = i // COLS
        x = col * CELL_W
        y = row * (CELL_H + LABEL_H) + 5
        frames = animations.get(name, [])
        if frames:
            frame = frames[0]
            ratio = min((CELL_W - 10) / frame.width,
                        (CELL_H - 10) / frame.height)
            nw, nh = max(1, int(frame.width * ratio)), max(1, int(frame.height * ratio))
            thumb = frame.resize((nw, nh), Image.LANCZOS)
            ox = x + (CELL_W - nw) // 2
            oy = y + (CELL_H - nh) // 2
            sheet.paste(thumb, (ox, oy), thumb)
        draw.text((x + CELL_W // 2, y + CELL_H + 2),
                  name.replace("_", " "),
                  fill=(205, 214, 244, 255), anchor="mt")
        draw.rectangle([x + 1, y + 1, x + CELL_W - 2, y + CELL_H - 2],
                       outline=(69, 71, 90, 255), width=1)

    sheet.save(out_path, "PNG")


                                                                                

def import_single(png_path: Path, height: int) -> None:
    print(f"\n🖼   Single-image import: {png_path}")

    if not png_path.exists():
        _die(f"File not found: {png_path}")
    if png_path.suffix.lower() not in (".png", ".webp", ".gif", ".jpg", ".jpeg"):
        print(f"  ⚠  '{png_path.suffix}' is not a PNG – will try anyway")

    base = _load_png(png_path)
    base = _crop_to_content(base)
    base = _resize_to_height(base, height)

    print(f"  ✓ Loaded sprite: {base.size[0]}×{base.size[1]} px RGBA")

                                
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    base.save(CUSTOM_BASE, "PNG")
                                                                         
    base.save(ASSETS_DIR / "konqi_base.png", "PNG")
    print(f"  ✓ Saved as custom base: {CUSTOM_BASE}")

    _clear_cache()

    print("\n🎬  Generating animation frames…")
    animations = _generate_all(base)

    _save_frames(animations, ASSETS_DIR)
    print(f"  ✓ {sum(len(v) for v in animations.values())} frames written to {FRAMES_DIR}")

    preview_path = ASSETS_DIR / "custom_preview.png"
    _print_contact_sheet(animations, preview_path)
    print(f"  ✓ Preview sheet saved → {preview_path}")

    _done_message()


def _generate_all(base: Image.Image) -> Dict[str, List[Image.Image]]:
    walk_r   = gen_walk_frames(base)
    walk_l   = [f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in walk_r]
    return {
        "walk_right":  walk_r,
        "walk_left":   walk_l,
        "idle":        gen_idle_frames(base),
        "sleep":       gen_sleep_frames(base),
        "climb_right": gen_climb_frames(base, direction="right"),
        "climb_left":  gen_climb_frames(base, direction="left"),
        "fall":        gen_fall_frames(base),
        "drag":        gen_drag_frames(base),
        "fly":         gen_fly_frames(base),
        "stretch":     gen_stretch_frames(base),
    }


                                                                                

def import_folder(folder: Path, height: int) -> None:
    print(f"\n📁  Folder import: {folder}")

    if not folder.is_dir():
        _die(f"Not a directory: {folder}")

    found_sets = [d.name for d in folder.iterdir()
                  if d.is_dir() and d.name in ANIM_NAMES]
    if not found_sets:
        _die(
            f"No recognisable animation folders found in '{folder}'.\n"
            f"Expected one or more of: {', '.join(ANIM_NAMES)}"
        )

                                                                     
    has_walk  = "walk_right" in found_sets
    has_idle  = "idle" in found_sets

    if not has_walk and not has_idle:
        _die(
            "Folder must contain at least a 'walk_right' or 'idle' sub-folder "
            "so missing animation sets can be auto-filled."
        )

    print(f"  Found sets: {sorted(found_sets)}")

                           
    loaded: Dict[str, List[Image.Image]] = {}
    for name in found_sets:
        pngs = sorted((folder / name).glob("*.png"))
        if not pngs:
            pngs = sorted((folder / name).glob("*.PNG"))
        if not pngs:
            print(f"  ⚠  '{name}/' is empty – skipping")
            continue
        frames = [_load_and_normalise(p, height) for p in pngs]
        frames = [f for f in frames if f is not None]
        if frames:
            loaded[name] = frames
            print(f"  ✓ {name}: {len(frames)} frame(s) @ {frames[0].size}")
        else:
            print(f"  ⚠  '{name}/' has no valid images – skipping")

    if not loaded:
        _die("No valid frames could be loaded from the folder.")

                                                                   
    fallback_base = _pick_fallback_base(loaded)
    animations = _fill_missing(loaded, fallback_base)

             
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    fallback_base.save(CUSTOM_BASE, "PNG")
    fallback_base.save(ASSETS_DIR / "konqi_base.png", "PNG")

    _clear_cache()
    _save_frames(animations, ASSETS_DIR)
    total = sum(len(v) for v in animations.values())
    print(f"\n  ✓ {total} frames written to {FRAMES_DIR}")

    preview_path = ASSETS_DIR / "custom_preview.png"
    _print_contact_sheet(animations, preview_path)
    print(f"  ✓ Preview sheet saved → {preview_path}")

    _done_message()


def _load_and_normalise(path: Path, height: int) -> Optional[Image.Image]:
    try:
        img = Image.open(path).convert("RGBA")
        img = _crop_to_content(img)
        img = _resize_to_height(img, height)
        return img
    except Exception as exc:
        print(f"    ⚠  Could not load '{path.name}': {exc}")
        return None


def _pick_fallback_base(loaded: Dict[str, List[Image.Image]]) -> Image.Image:
    """Pick the best single frame to use for generating missing sets."""
    for preferred in ("idle", "walk_right", "fall", "drag"):
        if preferred in loaded and loaded[preferred]:
            return loaded[preferred][0]
    return next(iter(loaded.values()))[0]


def _fill_missing(
    loaded: Dict[str, List[Image.Image]],
    base: Image.Image,
) -> Dict[str, List[Image.Image]]:
    """Combine user frames with auto-generated frames for missing sets."""
    generated = _generate_all(base)
    final: Dict[str, List[Image.Image]] = {}
    for name in ANIM_NAMES:
        if name in loaded:
            final[name] = loaded[name]
        else:
            final[name] = generated[name]
            print(f"  ↻ Auto-generated missing set: {name}")
    return final


                                                                                

def _done_message() -> None:
    print("""
╔══════════════════════════════════════════════════╗
║  ✅  Custom sprites imported successfully!       ║
║                                                  ║
║  Restart the shimeji to use your new sprites:   ║
║      python3 main.py                            ║
║                                                  ║
║  To revert to the built-in Konqi sprite:        ║
║      python3 import_sprite.py --reset           ║
╚══════════════════════════════════════════════════╝""")


                                                                                

def reset_to_default() -> None:
    print("\n🔄  Resetting to built-in Konqi sprite…")
    if CUSTOM_BASE.exists():
        CUSTOM_BASE.unlink()
        print("  ✓ Removed custom base")
                                                                                  
    default_base = ASSETS_DIR / "konqi_base.png"
    if default_base.exists():
        default_base.unlink()
        print("  ✓ Removed cached base (will re-download on next launch)")
    _clear_cache()
    print("\n  Restart main.py to use the built-in Konqi sprite.")


                                                                                

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import custom sprites into Konqi Shimeji",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "sprite",
        nargs="?",
        type=Path,
        metavar="SPRITE.PNG",
        help="Single PNG to use as the base sprite (auto-generates all animations)",
    )
    group.add_argument(
        "--folder", "-f",
        type=Path,
        metavar="DIR",
        help="Folder containing pre-made animation sub-folders",
    )
    group.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Remove custom sprites and revert to built-in Konqi",
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=SPRITE_HEIGHT,
        metavar="PX",
        help=f"Target sprite height in pixels (default: {SPRITE_HEIGHT})",
    )
    parser.add_argument(
        "--list-sets",
        action="store_true",
        help="List the animation set names expected in folder mode",
    )

    args = parser.parse_args()

    if args.list_sets:
        print("Expected animation folder names:")
        for n in ANIM_NAMES:
            req = " (required)" if n in ("walk_right", "idle") else " (optional)"
            print(f"  {n}{req}")
        print("\nFrames in each folder should be named: 01.png 02.png … (sorted order)")
        return

    if args.reset:
        reset_to_default()
        return

    if args.folder:
        import_folder(args.folder, args.height)
        return

    if args.sprite:
        import_single(args.sprite, args.height)
        return

                                   
    parser.print_help()
    print("\n── Quick examples ──────────────────────────────────────────────")
    print("  python3 import_sprite.py my_character.png")
    print("  python3 import_sprite.py my_character.png --height 128")
    print("  python3 import_sprite.py --folder ~/my_shimeji_sprites/")
    print("  python3 import_sprite.py --reset")
    print("  python3 import_sprite.py --list-sets")


if __name__ == "__main__":
    main()
