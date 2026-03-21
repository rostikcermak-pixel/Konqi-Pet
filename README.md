# konqi-shimeji

A Linux desktop pet that walks around your screen, judges everything you do, and occasionally has a breakdown about it.

Built on [PyQt6](https://pypi.org/project/PyQt6/). Runs on X11 and XWayland.

![Konqi walking around being chaotic](assets/konqi_idle.png)

---

## What he does

Konqi lives on your desktop. He walks, climbs screen edges, falls off things, and sleeps. Standard shimeji behaviour.

Everything else is his own doing.

He watches what you have open and comments on it. Opens YouTube at 11pm — he notices. Three hours in the same game — he's keeping count. Open his own source file — he has opinions. The longer you stay in something, the more pointed it gets.

Every few seconds something random happens: teleportation, tripping over nothing, summoning a second copy of himself to argue with, writing a bad poem about whatever app you have open, or freezing for two seconds and returning like nothing happened.

---

## Features

### Dialogue

- Reacts to 200+ specific apps and window titles — YouTube gets different lines than "browser", GitHub gets different lines than "code editor"
- Escalates the longer you stay in something — two minutes is a comment, two hours is a confrontation
- Remembers between sessions — tracks time per category and brings it up later
- Time-of-day and seasonal personality shifts
- Writes bad poems about whatever you have open. They are not good.
- Mysterious letters that arrive and get read aloud one line at a time

### Physics

- Walks, climbs walls, falls with gravity, bounces
- **Teleport** — shake → vanish → reappear with a bounce
- **Spin** — accelerates and decelerates smoothly
- **Drift** — eased movement with deceleration at target
- **Shake** — escalating circular amplitude
- **Dive** — launches with horizontal velocity using the fly animation
- **Trip** — multi-phase lurch with a small bounce recovery
- **Freeze glitch** — stops mid-stride, micro-stutters, snaps back confused
- **Flee cursor** — runs from your mouse on both axes, jumps if the cursor is above
- **Sit on windows** — teleports onto open windows and idles there
- **Stare at spots** — drifts to a random point, turns to look, walks away
- **Scribbles** — draws 2–4 fading doodles with words on your desktop
- **Summon twin** — spawns a second Konqi, they argue, the twin leaves

### Desktop integration

- Reacts to system notifications via `dbus-monitor`
- Detects wallpaper dominant colour and comments on your taste
- Detects if you open his source code
- Reacts to typing speed — fast, slow, stopping mid-sentence
- Gets more distressed with each additional clone spawned

### Sound effects *(off by default)*

Generated in pure Python — no audio files needed. Uses `pw-play`, `paplay`, `aplay`, or `ffplay` depending on what's installed. Includes footsteps, bounces, climb taps, drag squeak, bubble pop, scribble scratch, and a twin discord chord.

### Relationship progression

Comfort level increases with session count — starts formal, gets progressively more presumptuous. Saves to `gremlin_memory.json`. Delete it to reset his opinions of you. They will re-form quickly.

---

## Install

```bash
git clone https://github.com/yourusername/konqi-shimeji
cd konqi-shimeji
pip install PyQt6 Pillow psutil
python3 main.py
```

Or with the install script:

```bash
bash install.sh
```

**Steam Deck / SteamOS:**
```bash
pip install --break-system-packages PyQt6 Pillow psutil
python3 main.py
```

**Dependencies:** Python 3.10+, PyQt6 (or PyQt5), Pillow, psutil (optional but recommended). `xdotool` for app detection. Sound requires `pw-play`, `paplay`, or `aplay`.

---

## Usage

```
python3 main.py
python3 main.py --hyper          # faster, more chaotic
python3 main.py --count 3        # spawn 3 at once
python3 main.py --quiet          # no speech bubbles
python3 main.py --no-chaos       # just a normal walking dragon
```

Right-click Konqi for the full menu — chaos settings, animation speed, manual action triggers, sound toggle, autostart, and more.

---

## Custom sprites

Drop any PNG into `assets/` and run:

```bash
python3 import_sprite.py your_sprite.png
python3 main.py
```

Or right-click → Sprite: Change.

The project uses four sprites:

| File | Used for |
|---|---|
| `assets/konqi_walk.png` | Walking |
| `assets/konqi_idle.png` | Idle / pointing |
| `assets/konqi_sleep.png` | Sleeping (nose bubble built in) |
| `assets/konqi_climb.png` | Climbing |

Replace any of them and restart. Frame generation is automatic.

---

## Config

`config.json` in the project root:

| Key | Default | Description |
|---|---|---|
| `behavior_mode` | `"calm"` | `"calm"` or `"hyper"` |
| `chaos_mode` | `true` | The whole gremlin brain on/off |
| `quiet_mode` | `false` | Suppress speech bubbles |
| `sound_effects` | `false` | Sound on/off |
| `spawn_count` | `1` | How many spawn on startup |
| `fps` | `60` | Animation framerate |
| `cpu_reactions` | `true` | Sleeps when CPU is high |

---

## Project structure

```
konqi-shimeji/
├── main.py              Qt app — window, physics, chaos logic
├── chaos_gremlin.py     Brain — dialogue, app detection, memory, escalation
├── animation.py         State machine
├── physics.py           Gravity, walking, climbing
├── sprite_loader.py     Generates animation frames from source PNGs
├── sound_engine.py      Synthesises and plays sound effects
├── autostart.py         XDG autostart management
├── import_sprite.py     CLI tool for swapping sprites
└── assets/
    ├── konqi_walk.png
    ├── konqi_idle.png
    ├── konqi_sleep.png
    ├── konqi_climb.png
    └── frames/          Generated frames (auto-created)
```

---

## Notes

Works on X11 and XWayland. On pure Wayland without XWayland, window positioning still works but app detection (`xdotool`) won't. Tested on KDE, GNOME, and SteamOS.

The "PC tips" are fake. Please do not defragment your SSD.

---

## License

Code: MIT  
Konqi artwork: CC-BY-SA © KDE Contributors
