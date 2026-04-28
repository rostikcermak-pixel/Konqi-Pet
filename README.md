<div align="center">

# Konqi Pet 🐉

**A chaotic desktop pet for Linux - using KDE's own mascot**

*He walks. He climbs. He judges you. He has opinions about your tab count.*

![linux-kde](assets/linux-kde.gif)

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-supported-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20X11%2FXWayland-orange.svg)

</div>

---

Konqi is KDE's official mascot. He lives on your desktop now. He was not asked.

He walks around your screen, climbs the edges, falls off things, and falls asleep when you're boring. Every few seconds something random happens - he teleports, trips over nothing, summons a second copy of himself to argue with, or writes a bad poem about whatever you have open. He watches what apps you use and has escalating opinions the longer you stay in them.

<div align="center">

![konqi-kde](assets/konqi-kde.gif)

</div>

---

## What he does

- **Walks, climbs, falls, sleeps** - full physics with gravity, wall climbing, and bouncing
- **Watches your apps** - reacts to 200+ specific window titles with unique dialogue
- **Escalates** - two minutes open is a comment, two hours is a confrontation
- **Chaos events** - teleport, spin, drift, shake, dive, trip, glitch, stare, scribble, summon twin
- **Writes bad poems** about whatever you have open. They are not good.
- **Plays tic-tac-toe** with you and gets smug about it
- **Reacts to CPU, notifications, typing speed, wallpaper colour**
- **Remembers between sessions** - comfort level builds over time, delete `gremlin_memory.json` to reset his opinions of you (they will re-form quickly)

---

## Sprites

<div align="center">

| Walking | Idle | Sleeping | Climbing |
|:---:|:---:|:---:|:---:|
| ![walk](assets/konqi_walk.png) | ![idle](assets/konqi_idle.png) | ![sleep](assets/konqi_sleep.png) | ![climb](assets/konqi_climb.png) |

</div>

All animations are generated automatically from these four source PNGs - no sprite sheets needed.

---

## Install

```bash
git clone https://github.com/rostikcermak-pixel/Konqi-Pet
cd Konqi-Pet
pip install PyQt6 Pillow psutil
python3 main.py
```

**Steam Deck / SteamOS:**
```bash
pip install --break-system-packages PyQt6 Pillow psutil
python3 main.py
```

**Dependencies:** Python 3.10+, PyQt6 (or PyQt5), Pillow. `psutil` is optional but recommended. `xdotool` for app detection.

---

## Usage

```bash
python3 main.py                  # normal mode
python3 main.py --hyper          # faster, more chaotic
python3 main.py --count 3        # spawn 3 at once
python3 main.py --quiet          # no speech bubbles
python3 main.py --no-chaos       # just a normal walking dragon
```

Right-click Konqi for the menu - speed, chaos settings, tic-tac-toe, tips, actions, autostart, and updates.

---

## Custom sprites

Drop any PNG into `assets/` and run:

```bash
python3 import_sprite.py your_sprite.png
python3 main.py
```

The project uses four sprites - replace any and restart, frames regenerate automatically:

| File | Used for |
|---|---|
| `assets/konqi_walk.png` | Walking |
| `assets/konqi_idle.png` | Idle, pointing |
| `assets/konqi_sleep.png` | Sleeping |
| `assets/konqi_climb.png` | Climbing walls |

---

## Config

`config.json` in the project root:

| Key | Default | What it does |
|---|---|---|
| `behavior_mode` | `"calm"` | `"calm"` or `"hyper"` |
| `chaos_mode` | `true` | Enables the whole gremlin brain |
| `quiet_mode` | `false` | Suppresses speech bubbles |
| `sound_effects` | `false` | Footsteps, bounce, pop sounds |
| `spawn_count` | `1` | How many spawn on startup |
| `fps` | `60` | Animation framerate |
| `cpu_reactions` | `true` | Reacts when CPU is high |

---

## Notes

Works on X11 and XWayland. On pure Wayland without XWayland, movement works but app detection (`xdotool`) won't. Tested on KDE, GNOME, and SteamOS.

The PC tips are fake. Please do not defragment your SSD.

---

## License

Code: [MIT](LICENSE)  
Konqi artwork: CC-BY-SA © KDE Contributors
