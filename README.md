# konqi-shimeji

A Linux desktop pet that walks around your screen, judges everything you do, and occasionally has a breakdown about it.

Built on top of the original [Konqi Shimeji](https://kde.org) concept. Uses PyQt6, runs on X11/XWayland.

![Konqi walking around being chaotic](assets/konqi_preview.png)

---

## what it does

Konqi lives on your desktop. He walks back and forth, climbs the screen edges, falls off things, and sleeps occasionally. That part is normal shimeji behaviour.

The chaos part is everything else.

He watches what you have open and comments on it. Opens YouTube at 11pm — he notices. Been in the same game for three hours — he's keeping count. Open his own source file — he has opinions about that too. The longer you stay in something, the more pointed the commentary gets.

Every few seconds something random happens. He might teleport across the screen, trip over nothing, stare at a specific pixel for no reason, summon a second copy of himself to argue with, write a bad poem about whatever app you have open, or just freeze for two seconds and come back like nothing happened.

---

## features

**Dialogue system**
- Reacts to 200+ specific apps and window titles — not just categories, specific ones (YouTube gets different lines than "browser", GitHub gets different lines than "code editor")
- Escalates the longer you stay in something. Two minutes in a game is a comment. Two hours is a confrontation.
- Remembers between sessions. Tracks how long you've spent in each category and brings it up.
- Time-of-day personality. Different at 3am than at 9am.
- Seasonal lines. He knows what month it is.
- Bad poems. He will write one about whatever you have open. They are not good.
- Mysterious letters that arrive and get read aloud one line at a time.

**Physical chaos**
- Walks, climbs walls, falls with physics, bounces
- Teleport (shake → vanish → reappear with a bounce)
- Spin (accelerates and decelerates, not just direction flipping)
- Drift (eased acceleration with deceleration at target)
- Shake (escalating circular amplitude, not random jitter)
- Dive (launches with horizontal velocity, uses fly animation)
- Bounce (three decreasing bounces with timing)
- Trip (multi-phase lurch sequence with a small bounce recovery)
- Freeze glitch (stops mid-stride, micro-stutters at the end, snaps back confused)
- Flee cursor (runs from your mouse using both X and Y, jumps if cursor is above)
- Sit on window tops (teleports onto open windows and idles there)
- Stare at spots (drifts toward a random point, stares with head-turn animation, walks away)
- Scribbles (draws 2–4 fading doodles with words on your desktop)
- Summon twin (spawns a second Konqi, they argue, the twin leaves)

**Desktop integration**
- Reacts to system notifications (via dbus-monitor)
- Detects wallpaper dominant colour and comments on your taste
- Detects if you open his source code and comments on that specifically
- Typing speed reactions — fast typing, slow typing, stopping mid-sentence
- Clone count tracking — gets more distressed with each additional spawn

**Sound effects** (off by default)
- Generated in pure Python, no audio files needed
- Uses pw-play / paplay / aplay / ffplay depending on what's installed
- Footsteps, bounces, climb taps, drag squeak, bubble pop, scribble scratch, twin discord chord

**Relationship progression**
- Comfort level increases with session count — starts formal, gets progressively more presumptuous
- Remembers the last thing it said before you closed it
- Saves session data to `gremlin_memory.json`

---

## install

```bash
git clone https://github.com/yourusername/konqi-shimeji
cd konqi-shimeji

pip install PyQt6 Pillow psutil
python3 main.py
```

or with the install script:

```bash
bash install.sh
```

**Steam Deck / SteamOS:**
```bash
pip install --break-system-packages PyQt6 Pillow psutil
python3 main.py
```

**Dependencies:** Python 3.10+, PyQt6 (or PyQt5), Pillow, psutil (optional but recommended). `xdotool` for app detection. Sound needs `pw-play`, `paplay`, or `aplay`.

---

## usage

```
python3 main.py
python3 main.py --hyper          # faster, more chaotic
python3 main.py --count 3        # spawn 3 at once
python3 main.py --quiet          # no speech bubbles
python3 main.py --no-chaos       # just a normal walking dragon
```

Right-click on Konqi for the full menu — chaos settings, animation speed, force any action manually, sound toggle, autostart, etc.

---

## custom sprites

Drop any PNG into `assets/` and run:

```bash
python3 import_sprite.py your_sprite.png
python3 main.py
```

Or right-click → Sprite: Change.

The project uses four separate sprites for different states:
- `assets/konqi_walk.png` — walking
- `assets/konqi_idle.png` — idle / pointing pose
- `assets/konqi_sleep.png` — sleeping (nose bubble built into the sprite)
- `assets/konqi_climb.png` — climbing

Replace any of them and restart. Frame generation is automatic.

---

## config

`config.json` in the project root:

| key | default | what it does |
|---|---|---|
| `behavior_mode` | `"calm"` | `"calm"` or `"hyper"` |
| `chaos_mode` | `true` | the whole gremlin brain on/off |
| `quiet_mode` | `false` | suppresses speech bubbles |
| `sound_effects` | `false` | sound on/off |
| `spawn_count` | `1` | how many on startup |
| `fps` | `60` | animation framerate |
| `cpu_reactions` | `true` | reacts to high CPU by sleeping |

---

## project structure

```
konqi-shimeji/
├── main.py              Qt app, all window/physics/chaos logic
├── chaos_gremlin.py     brain — dialogue pools, app detection, memory, escalation
├── animation.py         state machine
├── physics.py           gravity, walking, climbing
├── sprite_loader.py     generates animation frames from source PNGs
├── sound_engine.py      synthesises and plays sound effects
├── autostart.py         XDG autostart management
├── import_sprite.py     CLI tool for swapping sprites
└── assets/
    ├── konqi_walk.png
    ├── konqi_idle.png
    ├── konqi_sleep.png
    ├── konqi_climb.png
    └── frames/          generated animation frames (auto-created)
```

---

## notes

Works on X11 and XWayland. On pure Wayland without XWayland, the window positioning still works but app detection (xdotool) won't. Tested on KDE, GNOME, and SteamOS.

Session memory is stored in `gremlin_memory.json` next to the script. Delete it to reset Konqi's opinions of you. They will re-form quickly.

The "PC tips" are fake. Please do not defragment your SSD.

---

## license

Code: MIT  
Konqi artwork: CC-BY-SA, © KDE Contributors
