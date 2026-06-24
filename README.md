<div align="center">

# 🐉 Konqi Pet

### A chaotic desktop pet for Linux — starring KDE's own mascot

*He walks. He climbs. He judges you. He has opinions about your tab count.*

<br>

![linux-kde](assets/linux-kde.gif)

<br>

[![License: MIT](https://img.shields.io/badge/License-MIT-8A2BE2.svg?style=for-the-badge)](LICENSE)
&nbsp;
![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)
&nbsp;
![PyQt](https://img.shields.io/badge/PyQt-6%20%2F%205-41CD52.svg?style=for-the-badge&logo=qt&logoColor=white)
&nbsp;
![Platform](https://img.shields.io/badge/Linux-X11%20%2F%20XWayland-FCC624.svg?style=for-the-badge&logo=linux&logoColor=black)

<br>

[**Install**](#-install) · [**What he does**](#-what-he-does) · [**Usage**](#-usage) · [**Config**](#-config) · [**Custom sprites**](#-custom-sprites)

</div>

---

Konqi is KDE's official mascot. He lives on your desktop now. He was not asked.

He walks around your screen, climbs the edges, falls off things, and falls asleep when you're boring. Every few seconds something random happens — he teleports, trips over nothing, summons a second copy of himself to argue with, or writes a bad poem about whatever you have open. He watches which apps you use and his opinions escalate the longer you stay in them.

<div align="center">

![konqi-kde](assets/konqi-kde.gif)

</div>

---

## ✨ What he does

| | |
|---|---|
| 🚶 **Moves like he means it** | Full physics — gravity, wall-climbing, falling, and bouncing |
| 👀 **Watches your apps** | Reacts to 200+ specific window titles with unique dialogue |
| 📈 **Escalates** | Two minutes open is a comment. Two hours is a confrontation. |
| 💥 **Causes chaos** | Teleport, spin, drift, shake, dive, trip, glitch, stare, scribble, summon twin |
| ✍️ **Writes bad poems** | About whatever you have open. They are not good. |
| 🎮 **Plays tic-tac-toe** | And gets smug about it (the AI is unbeatable) |
| 🌡️ **Reacts to your system** | CPU load, notifications, typing speed, even your wallpaper colour |
| 🧠 **Remembers you** | Comfort level builds across sessions — he greets you differently over time |

> [!TIP]
> To reset his opinion of you, delete `~/.local/share/konqi-pet/gremlin_memory.json`.
> (They will re-form quickly.)

---

## 📦 Install

**One line** — clones the repo, sets up a venv, and adds him to your app menu:

```bash
curl -fsSL https://raw.githubusercontent.com/rostikcermak-pixel/Konqi-Pet/main/install.sh | bash
```

<details>
<summary><b>Manual install</b></summary>

<br>

```bash
git clone https://github.com/rostikcermak-pixel/Konqi-Pet
cd Konqi-Pet
pip install PyQt6 Pillow psutil
python3 main.py
```

</details>

<details>
<summary><b>Steam Deck / SteamOS</b></summary>

<br>

```bash
pip install --break-system-packages PyQt6 Pillow psutil
python3 main.py
```

</details>

<details>
<summary><b>Flatpak (build it yourself)</b></summary>

<br>

See [`flatpak/README.md`](flatpak/README.md) for details.

```bash
flatpak install -y flathub org.kde.Platform//6.8 org.kde.Sdk//6.8
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.rostikcermak_pixel.KonqiPet.yaml
flatpak run io.github.rostikcermak_pixel.KonqiPet
```

</details>

> [!NOTE]
> **Dependencies:** Python 3.10+, PyQt6 (or PyQt5), Pillow.
> `psutil` is optional but recommended (CPU/RAM reactions). `xdotool` enables app detection.

---

## ⚡ Usage

```bash
python3 main.py                  # normal mode
python3 main.py --hyper          # faster, more chaotic
python3 main.py --count 3        # spawn 3 at once
python3 main.py --quiet          # no speech bubbles
python3 main.py --no-chaos       # just a normal walking dragon
```

**Right-click Konqi** for the full menu — speed, mode, chaos triggers, tic-tac-toe, tips, autostart, and updates.

---

## 🎨 Sprites

<div align="center">

| Walking | Idle | Sleeping | Climbing |
|:---:|:---:|:---:|:---:|
| ![walk](assets/konqi_walk.png) | ![idle](assets/konqi_idle.png) | ![sleep](assets/konqi_sleep.png) | ![climb](assets/konqi_climb.png) |

</div>

Every animation — walk, idle, sleep, climb, fall, stretch, wave, look-around — is **generated automatically** from these four source PNGs. No sprite sheets to draw.

---

## 🖌️ Custom sprites

Drop any PNG into `assets/` and run:

```bash
python3 import_sprite.py your_sprite.png
python3 main.py
```

Replace any of the four source sprites and restart — frames regenerate automatically:

| File | Used for |
|---|---|
| `assets/konqi_walk.png` | Walking |
| `assets/konqi_idle.png` | Idle, pointing, waving |
| `assets/konqi_sleep.png` | Sleeping |
| `assets/konqi_climb.png` | Climbing walls |

---

## ⚙️ Config

User settings live in `~/.config/konqi-pet/config.json` (shipped defaults are in [`config.json`](config.json)):

| Key | Default | What it does |
|---|:---:|---|
| `behavior_mode` | `"calm"` | `"calm"` or `"hyper"` |
| `chaos_mode` | `true` | Enables the whole gremlin brain |
| `quiet_mode` | `false` | Suppresses speech bubbles |
| `sound_effects` | `false` | Footsteps, bounce, pop sounds |
| `spawn_count` | `1` | How many spawn on startup |
| `fps` | `60` | Animation framerate |
| `cpu_reactions` | `true` | Reacts when CPU is high |

---

## 📝 Notes

- Works on **X11** and **XWayland**. On pure Wayland without XWayland, movement works but app detection (`xdotool`) won't.
- Tested on **KDE**, **GNOME**, and **SteamOS**.
- The "useless PC tips" are fake. Please do not defragment your SSD.

---

<div align="center">

## 📜 License

Code: [**MIT**](LICENSE) &nbsp;·&nbsp; Konqi artwork: **CC-BY-SA** © KDE Contributors

<br>

*Made for people who think their desktop is too calm.*

</div>
