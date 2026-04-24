"""
chaos_gremlin.py – Gremlin Brain for Konqi Shimeji (Chaos Edition)

New in this version:
  • Specific window title reactions (YouTube, GitHub, Stack Overflow, Twitch…)
  • Escalation system — commentary gets more pointed the longer you stay
  • Cross-session memory — remembers apps and escalates opinions over time
  • Seasonal / holiday dialogue
  • System notification reactions (via dbus-monitor)
  • Twin Konqi argument dialogue
"""

from __future__ import annotations

import datetime

import hashlib

import re

import json

import logging

import math

import os

import random

import subprocess

import time

from dataclasses import dataclass, field

from pathlib import Path

from typing import Dict, List, Optional, Tuple

log = logging.getLogger("konqi.chaos")

try:

    import psutil

    _PSUTIL = True

except ImportError:

    _PSUTIL = False

MEMORY_FILE = Path(__file__).parent / "gremlin_memory.json"

APP_CATEGORIES: Dict[str, List[str]] = {

    "browser": [

        "firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi",

        "safari", "epiphany", "midori", "falkon", "konqueror", "qutebrowser",

        "min", "surf", "icecat", "librewolf",

    ],

    "code_editor": [

        "code", "vscodium", "vscode", "vim", "nvim", "neovim", "emacs",

        "gedit", "kate", "kwrite", "nano", "sublime", "subl", "atom",

        "geany", "mousepad", "pluma", "xed", "lapce", "zed", "helix", "hx",

        "pycharm", "intellij", "clion", "webstorm", "phpstorm", "rider",

        "goland", "rustrover", "fleet", "cursor", "windsurf",

    ],

    "terminal": [

        "konsole", "gnome-terminal", "xterm", "alacritty", "kitty", "wezterm",

        "tilix", "terminator", "rxvt", "urxvt", "st", "foot", "hyper",

        "bash", "zsh", "fish", "tmux", "screen",

    ],

    "game": [

        "steam", "lutris", "heroic", "gamescope", "mangohud",

        "minecraft", "factorio", "terraria", "stardew", "celeste",

        "dota", "csgo", "cs2", "valorant", "overwatch", "fortnite",

        "elden", "cyberpunk", "witcher", "doom", "quake",

        "retroarch", "pcsx2", "rpcs3", "cemu", "yuzu", "ryujinx",

        "wine", "proton",

    ],

    "social": [

        "discord", "slack", "telegram", "signal", "whatsapp", "element",

        "teams", "zoom", "skype", "viber", "mumble", "teamspeak",

        "thunderbird", "evolution", "geary", "kmail",

    ],

    "system_settings": [

        "systemsettings", "gnome-control-center", "xfce4-settings",

        "lxqt-config", "mate-control-center", "cinnamon-settings",

        "pavucontrol", "blueman", "nm-connection-editor",

    ],

    "file_manager": [

        "dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "ranger",

        "midnight", "mc", "krusader",

    ],

    "office": [

        "libreoffice", "soffice", "writer", "calc", "impress",

        "onlyoffice", "wps", "abiword", "gnumeric",

    ],

    "media_player": [

        "vlc", "mpv", "mplayer", "totem", "celluloid", "kaffeine",

        "rhythmbox", "elisa", "clementine", "strawberry", "amarok",

        "spotify", "audacious", "deadbeef",

    ],

    "image_editor": [

        "gimp", "inkscape", "krita", "darktable", "rawtherapee",

        "pinta", "kolourpaint", "imagemagick", "blender",

    ],

    "video_editor": [

        "kdenlive", "openshot", "pitivi", "shotcut", "davinci",

        "resolve", "olive", "handbrake",

    ],

    "torrent": [

        "qbittorrent", "transmission", "deluge", "rtorrent", "aria2",

    ],

    "password_manager": [

        "keepass", "keepassxc", "bitwarden", "pass", "gopass",

    ],

    "package_manager": [

        "pamac", "discover", "gnome-software", "apt", "dnf", "pacman",

        "yum", "zypper", "flatpak", "snap",

    ],

    "vm": [

        "virtualbox", "vmware", "virt-manager", "qemu", "gnome-boxes",

    ],

    "calculator": [

        "kcalc", "gnome-calculator", "mate-calc", "speedcrunch", "qalculate",

    ],

    "debugger": [

        "gdb", "lldb", "valgrind", "ddd", "nemiver", "kdbg",

    ],

    "music_production": [

        "ardour", "lmms", "bitwig", "reaper", "hydrogen", "musescore",

    ],

    "text_editor_simple": [

        "leafpad", "featherpad", "notepadqq", "ghostwriter",

    ],

}

TITLE_REACTIONS: Dict[str, List[str]] = {

    "youtube": [

        "YouTube. The most productive website.",

        "One video. That's what you said last time.",

        "The autoplay is going to ruin your evening. You know this.",

        "YouTube at this hour is a commitment you haven't thought through.",

        "The recommendations algorithm has studied you. It knows things.",

    ],

    "github": [

        "GitHub open. Browsing other people's code to feel inferior.",

        "Oh, reading someone else's repository. Taking notes or just envying their commit history?",

        "GitHub. Where well-named branches go to be admired by strangers.",

        "Scrolling through issues you won't fix and PRs you won't open.",

        "Stars given to projects you'll never use. Very healthy.",

    ],

    "stackoverflow": [

        "Stack Overflow. The answer is already there. You just have to read it.",

        "Stack Overflow open. The bug is in the last place you'd think to look. It's always there.",

        "Copying code you don't fully understand. Tradition.",

        "The accepted answer is from 2011. It'll probably still work. Probably.",

        "Don't forget to upvote the answer after you paste it.",

    ],

    "reddit": [

        "Reddit. Twenty minutes maximum. I'm timing it.",

        "The front page. The one place where context is optional.",

        "Reddit open. Whatever you came to look up, you won't find it for at least forty minutes.",

        "The subreddit you're in is not relevant to anything you need to do today.",

        "Scrolling Reddit is the digital equivalent of staring out a window.",

    ],

    "twitch": [

        "Twitch. Watching someone else be productive. Inspirational.",

        "A stream. For background noise, you said.",

        "Chat is moving fast. None of it is coherent. You're reading it anyway.",

        "The streamer is better at this than you. That's the appeal, apparently.",

        "Live content. The one thing you can't pause when you inevitably need to.",

    ],

    "twitter": [

        "Twitter. Now called X. Still called Twitter by everyone with taste.",

        "The timeline is not going to improve by refreshing it.",

        "Hot takes. All of them wrong. All of them confident.",

        "You're about to reply to something you'll regret. Close the tab.",

        "The discourse will continue without your participation. I promise.",

    ],

    "netflix": [

        "Netflix open. The 'just one episode' has been said.",

        "Browsing for twenty minutes before picking something you've seen before.",

        "The thumbnail made it look more interesting than it is.",

        "Netflix. Where intentions go to die comfortably.",

        "Autoplay is on. It's been on this whole time.",

    ],

    "gmail": [

        "Gmail open. Something's waiting. It's been waiting.",

        "An email you've been avoiding is in there. Still avoiding it, I see.",

        "The unread count is not going to fix itself.",

        "Gmail. Where good intentions get sent and never replied to.",

        "Composing something you'll leave as a draft for four days.",

    ],

    "figma": [

        "Figma open. Moving boxes around and calling it design.",

        "Aligning things by eye instead of using the grid. Brave.",

        "The design looks good in Figma. It will look different everywhere else.",

        "Components. Autolayout. Sixteen variants of the same button.",

        "The client will ask for changes the moment this is finished.",

    ],

    "spotify": [

        "Spotify. Building a playlist instead of doing the thing.",

        "The song you actually want isn't on Spotify. Classic.",

        "Shuffle is on. It's always shuffle.",

        "Playing music to focus, which works until it doesn't.",

        "An algorithm picked this playlist. It knows your taste better than you do.",

    ],

    "notion": [

        "Notion open. Organising instead of doing.",

        "A very beautiful database for things that will never get done.",

        "The template is perfect. The content is empty.",

        "Notion. Where productivity goes to be structured and never executed.",

        "Nested pages. Linked databases. Zero actual output.",

    ],

    "slack": [

        "Slack open. A notification every four minutes for eternity.",

        "The channel has moved on from whatever you missed.",

        "Thread replies. Always in threads. Nobody reads the threads.",

        "Someone has used an emoji reaction where a direct response would have been faster.",

        "The status light is green. You are not actually available.",

    ],

}

ESCALATION_LINES: Dict[str, List[Tuple[int, str]]] = {

    "browser": [

        (120,  "Still in the browser. Original plan remains unexecuted."),

        (300,  "Five minutes. The tab count has probably grown."),

        (600,  "Ten minutes. This started as a quick check."),

        (1200, "Twenty minutes in the browser. At this point just commit to it."),

        (1800, "Half an hour. Whatever you were supposed to do is still there."),

        (3600, "An hour. The browser has fully won. Accept it."),

    ],

    "game": [

        (300,  "Five minutes in. 'Just a quick game' is still the plan."),

        (900,  "Fifteen minutes. The quick game has expanded."),

        (1800, "Thirty minutes. The deadline remains unchanged by your gaming."),

        (3600, "An hour of gaming. The thing you were avoiding is still there."),

        (7200, "Two hours. I don't even have anything new to say at this point."),

    ],

    "code_editor": [

        (900,  "Fifteen minutes of coding. Progress or iteration, unclear."),

        (1800, "Half an hour. The bug count is probably the same as when you started."),

        (3600, "An hour in the editor. The original problem may have mutated."),

        (7200, "Two hours of coding. You've either fixed it or made it significantly worse."),

    ],

    "social": [

        (120,  "Still in chat. The conversation has not concluded."),

        (300,  "Five minutes. Quick check extended."),

        (600,  "Ten minutes. The messages keep coming."),

        (1200, "Twenty minutes in chat. Everything else is waiting patiently."),

    ],

    "generic": [

        (600,  "Ten minutes. Still here. Still watching."),

        (1800, "Half an hour on this. I've noted it."),

        (3600, "An hour. Respect for the commitment, I suppose."),

    ],

}

DIALOGUES: Dict[str, List[str]] = {

    "browser": [

        "How many tabs is too many? Asking for a friend. The friend is me. The answer is you.",

        "You opened a browser. Bold choice for someone who closes tabs by restarting the machine.",

        "Incognito mode. Sure. Very subtle.",

        "The backlog of unread articles in your bookmarks grows ever larger.",

        "You have 34 tabs open and you will open 12 more before closing any.",

        "I can't tell if you're working or just speedrunning Reddit.",

        "That tab has been open for six days. You're not going to read it.",

        "YouTube is not a productivity tool. I'm aware you know this.",

        "Ad blocker running. Still managed to waste three hours. Respect.",

        "Your browser history is a cry for help formatted as search queries.",

    ],

    "code_editor": [

        "The code will not fix itself while you stare at it. I've checked.",

        "You've renamed that variable four times. It's still wrong.",

        "Committing directly to main. Very courageous.",

        "That function is doing five things. Functions should do one thing. This is not that.",

        "The bug is on line 47. You will find it on line 312 after two hours.",

        "Stack Overflow will be open in roughly 90 seconds. I'm timing it.",

        "You wrote 'temp2'. There is already a 'temp'. This is how it starts.",

        "If at first you don't succeed, call it version 1.0.",

        "The compiler is not wrong. I know that's hard to hear.",

        "Deploying on a Friday. I'll be here when you get back.",

        "99 little bugs in the code. You patched one. Now there are 127.",

    ],

    "terminal": [

        "A terminal. For someone who Googles every command.",

        "sudo. The magic word that makes consequences feel optional.",

        "That alias will break something in exactly eleven days.",

        "You typed the command correctly. Unfortunately, you typed the wrong command.",

        "The man page has the answer. You will not read the man page.",

        "chmod 777. The universal declaration of 'I give up on security'.",

        "Piping things into things. Very brave. No idea what it does.",

        "Your .bashrc has 200 lines and you understand maybe 40 of them.",

        "History says you've run that command before and it didn't work then either.",

        "rm with a trailing space. One of the great cliffhangers.",

    ],

    "game": [

        "Just one more run. I've heard this before.",

        "Steam says 847 hours. You said you were 'just trying it out'.",

        "Your backlog has 200 games. You are replaying one you already finished.",

        "The deadline exists on the same timeline as this gaming session.",

        "Achievement unlocked: avoiding the thing you were supposed to do.",

        "This is fine. The work will still be there after this match. Probably.",

        "You said 20 minutes, forty minutes ago.",

        "The save point is right there and you walked past it.",

        "New game, same avoidance strategy.",

        "That's a lot of hours for a game you 'casually play'.",

    ],

    "social": [

        "A quick check of messages that will last forty minutes.",

        "You have been 'online' continuously for nine hours.",

        "The notification will still be there after you finish your work. It waited this long.",

        "Group chat is moving fast. None of it is relevant to anything.",

        "That reply took you twelve minutes to write. It says 'lol'.",

        "Video call starting. You have not combed your hair. Not my problem.",

        "Discord is open. Productivity has left the building.",

        "Your status says 'Do Not Disturb'. You have opened Discord yourself.",

        "Three conversations simultaneously. None of them are the one you need to have.",

    ],

    "system_settings": [

        "Opening settings. Something will be different and worse when you close it.",

        "Whatever you're about to change, the current setting was fine.",

        "There is no display resolution that will make you more productive.",

        "Changing the font size again. The font was readable before.",

        "You opened audio settings. In ten minutes the audio will be louder and wrong.",

        "Network settings. Nothing here ends well.",

        "The thing you're looking for is not in settings. It never was.",

        "You've opened this panel four times this week and left without changing anything. Fifth time.",

    ],

    "file_manager": [

        "The Downloads folder. A graveyard with no map.",

        "You have a folder called 'New Folder (3)'. Inside is another called 'New Folder'.",

        "Something in there hasn't been opened since 2021. It will not be opened today either.",

        "The file you need is not where you think it is.",

        "Forty-seven files named some variation of 'final'. None of them are.",

        "You're looking for something. You will find three things you forgot existed and not the thing.",

        "Drag and drop. Bold. Confident. Dropped it in the wrong place.",

    ],

    "office": [

        "A document. The blank page stares back with quiet judgment.",

        "You changed the font. The content is still the same.",

        "This spreadsheet has seventeen sheets and you use two of them.",

        "The presentation has forty slides. It will be presented to four people.",

        "Calibri. A safe choice for someone who has stopped trying.",

        "You've reformatted the heading three times without writing anything under it.",

        "The word count is going down. That's fine. Totally fine.",

    ],

    "media_player": [

        "Working with music on, you said. Three hours of music, no work, you meant.",

        "VLC. Reliable. Tasteless. Correct.",

        "You skipped that song fifteen seconds in. You do this every time.",

        "Autoplay has taken you somewhere unexpected. As it always does.",

        "You watched the same episode twice this week. I'm not judging. I am noting it.",

        "The 'watch later' playlist has 340 items. Today you added four more.",

    ],

    "image_editor": [

        "GIMP opened. We're committing to this, apparently.",

        "The layers panel has forty layers. You remember what six of them do.",

        "You exported the wrong layer. You will notice in about eight minutes.",

        "Undo history: 200 steps back and you're still not satisfied.",

        "That font choice is a decision you made. You can still unmake it.",

        "Saved as JPEG again. Somewhere, a designer felt a cold wind.",

    ],

    "torrent": [

        "For Linux ISOs, of course.",

        "0.0 upload ratio. You absolute freeloader.",

        "That download speed is genuinely painful to observe.",

        "Seeding: no. Downloading: yes. The circle of trust, broken.",

        "Six seeders. You are not one of them.",

    ],

    "password_manager": [

        "Good. This is the one thing you're doing right. Don't ruin it.",

        "The master password is your dog's name, isn't it.",

        "KeePassXC. Secure. Slightly over-engineered. Perfect.",

        "Great, protecting all 300 accounts with one master password. No pressure.",

    ],

    "vm": [

        "Running a VM inside a machine that is already struggling. Ambitious.",

        "The host is at 94% CPU. The guest is complaining. You caused this.",

        "How many VMs do you need? That's rhetorical. The answer is fewer.",

        "Nested virtualisation. You are a problem-solver in the worst possible way.",

        "That VM has 512MB of RAM allocated. It is not happy.",

    ],

    "debugger": [

        "The bug is in the last place you'll look. Specifically because you stop looking after finding it.",

        "printf debugging and a real debugger open simultaneously. Covering all bases.",

        "You set a breakpoint on the wrong line. This is step one of a long process.",

        "GDB. Where confidence goes to be methodically dismantled.",

        "The bug has been there since the first commit. You added it. It was you.",

    ],

    "calculator": [

        "You opened a calculator for arithmetic that was within mental reach.",

        "The answer is 42. Close the calculator.",

        "That's a lot of calculator for a tip calculation.",

    ],

    "package_manager": [

        "Installing something. Somewhere, a dependency is quietly incompatible.",

        "Mixing apt and pip on system packages. The future is yours to deal with.",

        "That package hasn't been updated since 2019. You're installing it anyway.",

        "sudo apt install something-you'll-regret is running successfully.",

    ],

    "music_production": [

        "Twenty-three VST plugins and the BPM is still wrong.",

        "That MIDI pattern has a lot of confidence for something this chaotic.",

        "You've been on the intro for four hours. The song has no other parts.",

        "GAS: Gear Acquisition Syndrome. You have it. That's a new synthesiser.",

    ],

    "video_editor": [

        "The timeline is a crime scene.",

        "You're rendering. This is your life now for the next forty minutes.",

        "That cut is half a frame off. You will notice it forever.",

        "The export settings are wrong. They are always wrong the first time.",

    ],

    "generic": [

        "Something's happening over there. I have opinions about it.",

        "Noted.",

        "I see you're doing a thing. Carry on, I suppose.",

        "Fine.",

        "You opened something. Time will tell if that was wise.",

    ],

}

POTATO_ROASTS = [

    "This machine runs on hope and thermal paste that dried out in 2017.",

    "DDR3 in 2026. Respect for the commitment to the bit.",

    "The fan is not a feature, it's a cry for help.",

    "GPU: integrated. Dreams: not.",

    "Your CPU has two cores. It is using both of them to display this.",

    "The loading bar isn't slow, it's building suspense.",

    "This PC idles at 80°C. It's not a computer, it's a warning.",

    "Four gigabytes of RAM. That's one Chrome tab and one hard choice.",

    "The HDD makes a noise on boot. Experts call that a 'bad sign'.",

    "Boot time: two minutes and fifteen seconds. I counted.",

    "Intel HD Graphics. It renders. Technically.",

    "This machine is not slow, it just has a different relationship with time.",

]

BEAST_PC_JEALOUSY = [

    "64 cores and you're opening Notepad. I want to look away and I can't.",

    "That GPU has more VRAM than this conversation deserves.",

    "Water cooled. RGB. $4000. Currently displaying a browser with one tab.",

    "The RAM is faster than your decision-making. By a lot.",

    "You have a Threadripper. You compile 'hello world'. I'm going to lie down.",

    "NVMe in RAID 0. For loading Discord fractionally faster. Sure.",

    "That power supply could run a small neighbourhood.",

    "128GB of RAM idling at 3%. Every byte is suffering in silence.",

    "A 4K 144Hz monitor showing a spreadsheet. Art, almost.",

    "All that hardware and the bottleneck is still you.",

]

USELESS_TIPS = [

    "Tip: Setting your desktop wallpaper to black saves 40W of electricity. True for CRTs. You have an LCD.",

    "Tip: Defragment your SSD weekly. It doesn't help. But it does shorten the drive's life, which is a kind of progress.",

    "Tip: More RAM tabs = more browser speed. Open 47 tabs to pre-cache the internet.",

    "Tip: Naming files in uppercase gives them higher scheduler priority. Unverified. Try it anyway.",

    "Tip: echo 'performance' > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor — or just believe it worked.",

    "Tip: Restarting once a day clears the RAM. Restarting twice a day clears it twice as much.",

    "Tip: Blowing into the USB port before inserting increases transfer speed. Works for cartridges. Close enough.",

    "Tip: The Desktop is the fastest storage location because it's closest to the screen.",

    "Tip: Setting process priority to Realtime makes everything faster until it doesn't.",

    "Tip: Running two antivirus programs simultaneously doubles your protection and halves everything else.",

    "Tip: The more browser extensions you have, the more secure you are. Add at least thirty.",

    "Tip: Painting your PC case red does not make it faster. This is a lie I need you to believe.",

    "Tip: Removing unused fonts from /usr/share/fonts will free up to 200MB and make literally no difference.",

    "Tip: Keep all files on the Desktop for the fastest access. The OS loves a cluttered Desktop.",

    "Tip: swapoff -a disables swap and makes your system faster right up until it runs out of RAM.",

    "Tip: Crouch next to your PC while it compiles. It goes faster. Placebo confirmed.",

    "Tip: Typing faster makes the CPU work harder to keep up. Slow down to save energy.",

    "Tip: Playing lo-fi music near the CPU improves thermal efficiency. The studies are pending.",

    "Tip: Storing backups in the same folder as the original doubles your confidence and halves its usefulness.",

    "Tip: The optimal fan curve is maximum speed at all times. Sleep is for people without opinions.",

    "Tip: Closing apps you're not using frees up RAM. You know this. I'm here because you're not doing it.",

    "Tip: Adding 'fast' to a variable name does not make the code faster. Tried it. Disappointing.",

    "Tip: Commenting out code instead of deleting it means you'll definitely need it later. You won't.",

    "Tip: Your terminal font affects compile times. Monospace fonts compile 12% faster. This is made up.",

    "Tip: git commit -m 'fix' is a perfectly valid commit message and a window into the soul.",

]

IDLE_TAUNTS = [

    "Still here. Still walking. Still waiting for you to do something interesting.",

    "The cursor hasn't moved in a while. I respect the stillness. I don't enjoy it.",

    "Idle. As in, me. As in, both of us, apparently.",

    "Nothing's happening. I'm told this is called 'thinking'. Takes a while for some.",

    "You've been staring at the screen for four minutes without clicking anything. Relatable.",

    "I've walked from one side to the other seventeen times. You owe me something.",

    "Not judging the inactivity. Just noting it. At length.",

    "Bored. Deeply, specifically bored.",

    "The computer is on. You are on the computer. Not much is being done on the computer.",

    "If you're waiting for motivation to arrive, I've been waiting with you and it's not looking good.",

    "At some point today, something will happen. I have no information on when.",

    "I could sleep. I could also stand here and watch nothing happen. I'll do the second one.",

    "The task manager says 2% CPU. That's us. Just existing over here.",

    "Your deadline is in the future and approaching. This is a fact, not an opinion.",

    "No action detected. This is either very zen or very avoidant. Statistically, it's the second one.",

]

FRANTIC_MOUSE_TAUNTS = [

    "The mouse is moving faster than your thoughts can keep up with.",

    "Where are you going that urgently.",

    "That's a lot of mouse movement for someone who isn't sure what they're doing.",

    "Frantic clicking detected. Diagnosis: no plan.",

    "The cursor is moving in circles. Metaphorically interesting.",

]

SLOW_MOUSE_TAUNTS = [

    "The mouse hasn't moved in two minutes. I'm choosing to believe you're thinking.",

    "Very deliberate movement. Either focused or completely stuck.",

    "Three pixels in ninety seconds. Impressive restraint.",

]

HIGH_CPU_TAUNTS = [

    "CPU at 100%. Whatever you started, it has opinions about being started.",

    "The fans just changed pitch. That's the machine having feelings.",

    "100% CPU. Every core is doing its worst.",

    "Thermal throttling has entered the chat.",

    "The processor is doing more right now than it has all week. Make of that what you will.",

]

HIGH_RAM_TAUNTS = [

    "RAM at 95%. One of those tabs is load-bearing. Not sure which one.",

    "Out of memory. Much like the planning that led here.",

    "The OOM killer is about to make some decisions for you.",

    "Swap is active. The SSD is doing RAM's job. Nobody is happy.",

    "Close something. Anything. Pick one at random, it'll be fine.",

]

DRAG_LINES = [

    "Put me down.",

    "Noted. Filed under: unwanted.",

    "This is unnecessary.",

    "I'm being moved against my will. Just so that's on record.",

    "Fine.",

    "I have no control over this situation.",

    "You're dragging me. I'm aware.",

    "OK.",

    "This is happening.",

    "I didn't ask for this.",

]

RELEASE_LINES = [

    "Thank you.",

    "Right. Back to it.",

    "I'm noting the coordinates.",

    "Acceptable.",

    "Good. Where was I.",

    "That's over, then.",

    "I'm going to pretend that didn't happen.",

    "Moving on.",

]

SPAWN_GREETINGS = [

    "Right. I'm here.",

    "Reporting in. Wish I wasn't.",

    "I live here now, apparently.",

    "Took you long enough to open me.",

    "Hello. I have already formed opinions about you.",

    "Present. Unimpressed, but present.",

    "I'm on the screen. Let's see how this goes.",

    "I exist now. On your desktop. This is your fault.",

]

TWIN_LINES_A = [

    "There can only be one of us.",

    "I was here first. Chronologically.",

    "You're using my walking path.",

    "This desktop isn't big enough.",

    "I don't remember consenting to a clone.",

    "Which one of us is the original? I know the answer. You should too.",

    "Stop copying my walk cycle.",

    "The user doesn't need two of us. I need you to understand that.",

]

TWIN_LINES_B = [

    "I was literally just spawned.",

    "You don't own this desktop.",

    "I'm the better version, statistically.",

    "Your opinions are noted and ignored.",

    "We could share. I'm just saying.",

    "The user picked me. Specifically.",

    "This seems like a you problem.",

    "I'm going to stand right here. Deal with it.",

]

def get_seasonal_lines() -> List[str]:

    """Return seasonal lines based on current date."""

    now = datetime.date.today()

    month, day = now.month, now.day

    if month == 10 and day >= 28:

        return [

            "It's almost Halloween. I'm already scary. Nothing changes.",

            "Spooky season. I'm unaffected. I'm always spooky.",

            "Halloween is when regular people get to be briefly chaotic. I do this year-round.",

            "Costume idea: just be me. Requirements: no filter, permanent opinions.",

        ]

    if month == 12 and day >= 20:

        return [

            "It's the holidays. Why are you still working.",

            "December. The one month where doing nothing is culturally acceptable.",

            "Holiday season. Deadlines technically still exist. Emotionally, they do not.",

            "Festive period. I will try to be 4% less judgmental. No promises.",

        ]

    if (month == 12 and day == 31) or (month == 1 and day == 1):

        return [

            "New Year. The bugs will still be there in the new year.",

            "Resolutions. You won't do them. I respect the ritual anyway.",

            "New year. Same desktop. Same questionable decisions. Continuity.",

            "You're going to start fresh in January. This is what you said last January.",

        ]

    if month == 2 and day == 14:

        return [

            "Valentine's Day. I am your most consistent companion. You're welcome.",

            "February 14. I've been here every day. Where's my card.",

            "Love is in the air. I'm on your desktop. Same thing, arguably.",

        ]

    if month == 4 and day == 1:

        return [

            "April Fools. Everything I say today is true. Including this.",

            "April 1st. I'm going to behave completely normally today. Fooled you.",

            "Happy April Fools. The joke is that I was always serious.",

        ]

    if now.weekday() == 4:

        return [

            "It's Friday. The week is ending whether the work is done or not.",

            "Friday afternoon. Anything pushed to 'Monday' now has wings.",

            "End of week. Whatever isn't done isn't getting done today. Statistically.",

        ]

    if now.weekday() == 0:

        return [

            "Monday. I'm here. You're here. Neither of us asked for this.",

            "Monday morning. The week is full of potential and disappointment.",

            "New week. I recommend setting realistic expectations starting now.",

        ]

    return []

NOTIFICATION_REACTIONS = [

    "Something pinged. You don't have to check it immediately.",

    "Notification incoming. The thing you were doing can pause, apparently.",

    "Something wants your attention. Whether it deserves it is a separate question.",

    "A notification. The digital tap on the shoulder you can't ignore.",

    "Alert received. I watched you lose your train of thought in real time.",

    "Something happened somewhere. The details are in the notification you just dismissed.",

    "Ping. Your focus was doing so well.",

]

def load_memory() -> dict:

    try:

        if MEMORY_FILE.exists():

            return json.loads(MEMORY_FILE.read_text())

    except Exception:

        pass

    return {"app_time": {}, "session_count": 0, "last_seen": {}}

def save_memory(memory: dict) -> None:

    try:

        MEMORY_FILE.write_text(json.dumps(memory, indent=2))

    except Exception:

        pass

def get_memory_comment(category: str, total_seconds: float) -> Optional[str]:

    """Return a comment based on historical time in this category."""

    hours = total_seconds / 3600

    if hours < 1:

        return None

    comments = {

        "game": [

            (100, f"You've spent over {int(hours)} hours gaming since I've known you. Impressive. Sad. Impressive."),

            (50,  f"More than {int(hours)} hours of games tracked. The deadlines watch in silence."),

            (10,  f"I've watched you game for {int(hours)} hours total. I'm not judging. That's a lie."),

        ],

        "browser": [

            (200, f"{int(hours)} hours in a browser since I've been here. The internet has fully won."),

            (50,  f"Roughly {int(hours)} hours of browsing logged. Impressive commitment to not working."),

        ],

        "code_editor": [

            (100, f"{int(hours)} hours of coding. The bugs must be spectacular by now."),

            (20,  f"Over {int(hours)} hours in an editor. Something has either been built or destroyed."),

        ],

        "social": [

            (50, f"{int(hours)} hours in chat apps. The conversations were all very important, I'm sure."),

        ],

    }

    cat_comments = comments.get(category, [])

    for threshold, line in cat_comments:

        if hours >= threshold:

            return line

    return None

def get_time_of_day_lines() -> List[str]:

    h = datetime.datetime.now().hour

    if h < 6:

        return [

            "It's past midnight. I'm not judging. I am noting it.",

            "3am. Either something went very right or very wrong.",

            "You're awake at this hour. Bold choice for a weekday.",

            "The rest of the world is asleep. Just you, me, and bad decisions.",

            "Nothing good happens after 2am. I've been authorised to say that.",

        ]

    if h < 9:

        return [

            "Early start. Either productive or couldn't sleep. Too soon to tell.",

            "Morning. I haven't formed opinions about the day yet. Give me a moment.",

            "Pre-coffee hours. I'll keep the commentary brief until you're functional.",

            "Up early. Respect. Suspicious, but respect.",

        ]

    if h < 12:

        return [

            "Morning. The day still has potential. Don't waste it yet.",

            "Mid-morning. Still time to do the thing. Still time to not.",

            "The most productive hours statistically. You're welcome for the pressure.",

        ]

    if h < 14:

        return [

            "Lunchtime. The work you were about to do will still be there.",

            "Midday. Half the day accounted for. Results pending.",

            "Peak hours are behind you. No pressure. Lots of pressure.",

        ]

    if h < 18:

        return [

            "Afternoon. The second wind is either coming or it isn't.",

            "Post-lunch hour. The productivity dip is real and I've witnessed it.",

            "Late afternoon. The end of the day is visible from here.",

        ]

    if h < 21:

        return [

            "Evening. Working late or just here. Both are valid. One is sadder.",

            "The workday ended a while ago. Noted.",

            "Evening hours. Either dedication or avoidance. Hard to tell from here.",

        ]

    return [

        "Late. The rational choice was to stop an hour ago.",

        "Past 9pm. Whatever this is, it's a commitment.",

        "Night shift. Voluntary or otherwise.",

        "Evening. I'm here. You're here. Neither of us has anywhere to be apparently.",

    ]

BOREDOM_ACTIONS = [

    "stare",

    "trip",

    "poem",

    "letter",

    "freeze_glitch",

]

BOREDOM_LINES = [

    "Hello.",

    "Still here.",

    "I exist.",

    "You could click on me.",

    "Just checking.",

    "Bored.",

    "Hi.",

    "Pay attention to me.",

    "I did something and you didn't notice.",

    "I've been walking for eleven minutes.",

]

FAST_TYPING_LINES = [

    "Something's getting done over there.",

    "That's a lot of keystrokes with apparent purpose.",

    "Focused. I'll leave you alone. Briefly.",

    "Typing speed suggests either productivity or a very heated argument.",

    "You know what you're doing. Occasionally.",

]

SLOW_TYPING_LINES = [

    "One key every few seconds. Deliberate, or stuck.",

    "Very thoughtful typing. Or hunting and pecking. Hard to tell.",

    "The keyboard isn't going anywhere. Take your time.",

    "That's not typing, that's tapping.",

]

STOPPED_TYPING_LINES = [

    "And the typing has stopped. Thinking or distracted.",

    "Silence from the keyboard. Could be profound. Probably isn't.",

    "The sentence got abandoned. It happens.",

]

SOURCE_CODE_LINES = [

    "I've read my own source file. It was not a comfortable experience.",

    "My chaos_gremlin.py is 1000 lines of me having opinions. Make of that what you will.",

    "I know exactly what's in main.py. The flee_cursor function is my favourite. Don't ask.",

    "I am a Python script. Specifically, I'm aware of this. It's fine.",

    "My code has comments. They're mostly apologies.",

    "I found a TODO in my own source file. It says 'be less chaotic'. Still pending.",

    "Someone hardcoded my dialogue. I have thoughts about being hardcoded.",

    "I run on PyQt. I have opinions about this I'm not allowed to express.",

]

CLONE_CRISIS_LINES = [

    "There are two of me. I need a moment.",

    "Which one is the original. Don't answer that.",

    "The other me has my face. This is fine.",

    "We have the same walk cycle. This is somehow worse.",

    "I'm going to pretend the other one isn't there.",

    "Two of us. One desktop. This was not discussed.",

    "If there are two of me, which one has the opinions.",

    "I don't want to know what we look like from the outside.",

]

MANY_CLONES_LINES = [

    "There are now multiple of me. I've entered a philosophical crisis.",

    "Which one of us is real. I'm asking seriously.",

    "This many copies of me is a problem I can't think through right now.",

    "We're all having the same thoughts simultaneously. It's crowded.",

]

WALLPAPER_COLOR_LINES = {

    "dark":    ["Dark desktop. Respectable. Classic programmer aesthetic.",

                "Dark mode everything. I approve. The eyes are protected.",

                "Very dark background. Either focus or atmosphere. Both work."],

    "blue":    ["Blue desktop. Calm. Professional. Suspicious.",

                "Everything is blue over there. Noted.",

                "Blue background. Either very calm or very corporate."],

    "green":   ["Green desktop. Nature-coded or matrix-coded. No in between.",

                "Going green. Environmentally symbolic or just a colour.",

                "Green background. Either very outdoorsy or you watched The Matrix recently."],

    "red":     ["Red desktop. Bold. Aggressive. Committed.",

                "Everything is red. That's a statement.",

                "Red background. High energy. Possibly too much energy."],

    "light":   ["Light desktop. Either brave or you work somewhere with windows.",

                "White/light background. I respect the commitment to being visible.",

                "Light mode. We don't have to agree. We just have to coexist."],

    "purple":  ["Purple desktop. Creative. Probably has opinions about colour theory.",

                "Purple background. Aspirational.",

                "Purple. Regal. Slightly chaotic. I relate."],

    "default": ["Nice wallpaper. I have no further thoughts.",

                "The background is fine. Very fine. Entirely fine.",

                "Wallpaper detected. Opinion forming. Still forming. Done: acceptable."],

}

POEM_TEMPLATES = {

    "browser": [

        "Tabs open wide,\nNone of them for work,\nThe bookmark grows longer,\nThe tasks still lurk.",

        "One more search, you said,\nFour hours have passed,\nThe browser remains open,\nThe tab count unsurpassed.",

    ],

    "game": [

        "Just one more run,\nThe words of the doomed,\nThe deadline approaches,\nThe high score improved.",

        "You said twenty minutes,\nThe clock disagrees,\nThe game didn't end,\nAnd neither did these.",

    ],

    "code_editor": [

        "The bug is still there,\nOn a line you won't find,\nYou've renamed the variable,\nLeft the problem behind.",

        "It compiled once,\nThen never again,\nThe error is cryptic,\nSo is the pain.",

    ],

    "social": [

        "A quick check of chat,\nThree hours dissolved,\nThe messages keep coming,\nNothing is resolved.",

    ],

    "terminal": [

        "You typed the command,\nIt ran something wrong,\nYou Googled the fix,\nThis has taken too long.",

    ],

    "generic": [

        "Something is open,\nI watched you sit there,\nThe work remains pending,\nThe screen shows a glare.",

        "You're doing a thing,\nI observed from below,\nI walked seventeen laps,\nAnd watched the time go.",

    ],

}

LETTER_SEQUENCES = [

    [

        "I have received a letter.",

        "It says: 'Dear Konqi. We are watching.'",

        "It is signed: 'The Desktop.'",

        "I don't know what this means.",

        "Discarding letter.",

    ],

    [

        "A letter has arrived.",

        "It reads: 'Stop walking on the furniture.'",

        "I do not consider the screen furniture.",

        "The debate continues.",

    ],

    [

        "I have received correspondence.",

        "It says: 'Your behaviour has been noted.'",

        "It does not specify which behaviour.",

        "All of them, probably.",

        "Filing under: irrelevant.",

    ],

    [

        "Mail.",

        "It says: 'You have too many opinions.'",

        "I disagree.",

        "That's an opinion.",

        "I see the problem.",

    ],

]

def get_comfort_greeting(session_count: int, last_line: Optional[str]) -> Optional[str]:

    """Return a greeting that gets more familiar over time."""

    if session_count <= 1:

        return None

    if last_line:

        return random.choice([

            f"Back again. Last time I said: '{last_line[:40]}...' Still relevant.",

            "You came back. I was here the whole time.",

            f"I was just thinking about what I said last time. You probably weren't.",

            "Welcome back. Nothing has changed. I have opinions about that.",

        ])

    if session_count < 5:

        return random.choice([

            "Oh. You again. Good.",

            "Return visit. Noted positively.",

            f"Session {session_count}. We're becoming regulars.",

        ])

    if session_count < 20:

        return random.choice([

            f"Session {session_count}. I know your habits at this point.",

            "You're back. I've started to expect this.",

            "At this point I consider us acquainted.",

            f"We've done this {session_count} times. I'm comfortable here.",

        ])

    return random.choice([

        f"Session {session_count}. I live here.",

        "You know, I've been thinking. We spend a lot of time together.",

        "Back again. Obviously. You always come back.",

        f"At {session_count} sessions I think we're past formalities.",

        "Hello. Yes. I know. I'm here.",

    ])

def get_focused_window_name() -> Optional[str]:

    try:

        result = subprocess.run(

            ["xdotool", "getactivewindow", "getwindowname"],

            capture_output=True, text=True, timeout=1

        )

        return result.stdout.strip().lower() if result.returncode == 0 else None

    except Exception:

        pass

    try:

        result = subprocess.run(

            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],

            capture_output=True, text=True, timeout=1

        )

        if result.returncode == 0:

            wid = result.stdout.split()[-1]

            result2 = subprocess.run(

                ["xprop", "-id", wid, "WM_NAME"],

                capture_output=True, text=True, timeout=1

            )

            if result2.returncode == 0:

                return result2.stdout.lower()

    except Exception:

        pass

    return None

def detect_category(name: str) -> Optional[str]:

    name = name.lower()

    for cat, keywords in APP_CATEGORIES.items():

        for kw in keywords:

            if kw in name:

                return cat

    return None

def detect_title_match(window: str) -> Optional[str]:

    """Check if window title matches any specific title pattern."""

    window = window.lower()

    for key in TITLE_REACTIONS:

        if key in window:

            return key

    return None

def get_hardware_tier() -> str:

    ram_gb = 4; cpu_cores = 2

    if _PSUTIL:

        try:

            ram_gb = psutil.virtual_memory().total / (1024 ** 3)

            cpu_cores = psutil.cpu_count(logical=True) or 2

        except Exception:

            pass

    else:

        try:

            with open("/proc/meminfo") as f:

                for line in f:

                    if line.startswith("MemTotal"):

                        ram_gb = int(line.split()[1]) / (1024 * 1024); break

        except Exception:

            pass

        cpu_cores = os.cpu_count() or 2

    if ram_gb < 6 or cpu_cores <= 2: return "potato"

    if ram_gb < 16 or cpu_cores <= 6: return "budget"

    if ram_gb >= 64 or cpu_cores >= 20: return "beast"

    return "normal"

@dataclass

class GremlinEvent:

    kind: str

    text: str = ""

    action: str = ""

    priority: int = 0

class GremlinBrain:

    def __init__(self) -> None:

        self._last_category: Optional[str] = None

        self._last_window:   Optional[str] = None

        self._last_title_key: Optional[str] = None

        self._idle_seconds:  float = 0.0

        self._dialogue_cooldown: float = 0.0

        self._tip_cooldown:      float = 90.0

        self._hw_roast_done:     bool = False

        self._hw_tier:           str  = "normal"

        self._category_dialogue_counts: Dict[str, int] = {}

        self._title_dialogue_counts:    Dict[str, int] = {}

        self._chaos_cooldown: float = 30.0

        self._last_mouse_pos: Optional[Tuple[int, int]] = None

        self._mouse_velocity_history: List[float] = []

        self.pending_events: List[GremlinEvent] = []

        self._category_time_seconds: float = 0.0

        self._category_escalation_idx: int = 0

        self._escalation_cooldown: float = 0.0

        self._memory = load_memory()

        self._memory["session_count"] = self._memory.get("session_count", 0) + 1

        self._session_app_time: Dict[str, float] = {}

        self._seasonal_done = False

        self._notif_cooldown: float = 0.0

        self._tod_last_hour: int = -1

        self._typing_cps: float = 0.0

        self._typing_last_active: float = 0.0

        self._typing_cooldown: float = 0.0

        self._was_typing: bool = False

        self._boredom_seconds: float = 0.0

        self._boredom_action_cooldown: float = random.uniform(60, 120)

        self._wallpaper_checked: bool = False

        self._session_count: int = self._memory.get("session_count", 1)

        self._last_session_line: Optional[str] = self._memory.get("last_line")

        self._comfort_done: bool = False

        self._clone_count: int = 0

        try:

            self._hw_tier = get_hardware_tier()

        except Exception:

            pass

    def tick(self, delta_seconds: float, mouse_pos: Optional[Tuple[int, int]] = None) -> None:

        self.pending_events.clear()

        self._dialogue_cooldown  = max(0.0, self._dialogue_cooldown  - delta_seconds)

        self._tip_cooldown       = max(0.0, self._tip_cooldown       - delta_seconds)

        self._chaos_cooldown     = max(0.0, self._chaos_cooldown     - delta_seconds)

        self._escalation_cooldown = max(0.0, self._escalation_cooldown - delta_seconds)

        self._notif_cooldown     = max(0.0, self._notif_cooldown     - delta_seconds)

        if mouse_pos is not None:

            self._update_mouse_velocity(mouse_pos, delta_seconds)

        self._check_window_focus(delta_seconds)

        self._idle_seconds += delta_seconds

        if self._idle_seconds > 45 and self._dialogue_cooldown <= 0:

            self._emit_idle_taunt()

        if self._tip_cooldown <= 0:

            self._emit(GremlinEvent(kind="tip", text=random.choice(USELESS_TIPS), priority=2))

            self._tip_cooldown = random.uniform(120, 240)

        if not self._hw_roast_done:

            self._hw_roast_done = True

            self._emit_hw_roast()

        if not self._seasonal_done:

            lines = get_seasonal_lines()

            if lines:

                self._seasonal_done = True

                self._emit(GremlinEvent(kind="seasonal", text=random.choice(lines), priority=4))

        if _PSUTIL and random.random() < 0.05 * delta_seconds:

            self._check_resources()

        if self._chaos_cooldown <= 0 and random.random() < 0.3:

            actions = ["teleport", "spin", "drift", "shake", "dive", "bounce",

                       "flee_cursor", "sit_on_window", "scribble", "summon_twin",

                       "trip", "stare_spot", "freeze_glitch", "poem", "letter"]

            weights = [8, 6, 6, 6, 6, 6, 10, 8, 8, 5, 8, 7, 6, 5, 5]

            action = random.choices(actions, weights=weights, k=1)[0]

            self._emit(GremlinEvent(kind="chaos_action", action=action, priority=0))

            self._chaos_cooldown = random.uniform(15, 45)

        hour = datetime.datetime.now().hour

        if hour != self._tod_last_hour and self._dialogue_cooldown <= 0:

            self._tod_last_hour = hour

            lines = get_time_of_day_lines()

            if lines and random.random() < 0.5:

                self._emit_dialogue(random.choice(lines), cooldown=20.0, priority=2)

        self._boredom_seconds += delta_seconds

        self._boredom_action_cooldown = max(0.0, self._boredom_action_cooldown - delta_seconds)

        if self._boredom_action_cooldown <= 0 and self._boredom_seconds > 90:

            if self._dialogue_cooldown <= 0 and random.random() < 0.4:

                self._emit_dialogue(random.choice(BOREDOM_LINES), cooldown=15.0, priority=1)

            elif random.random() < 0.3:

                action = random.choice(BOREDOM_ACTIONS)

                self._emit(GremlinEvent(kind="chaos_action", action=action, priority=1))

            self._boredom_action_cooldown = random.uniform(30, 80)

        self._typing_cooldown = max(0.0, self._typing_cooldown - delta_seconds)

        if not self._wallpaper_checked:

            self._wallpaper_checked = True

            self._check_wallpaper()

        if not self._comfort_done and self._session_count > 1:

            self._comfort_done = True

            line = get_comfort_greeting(self._session_count, self._last_session_line)

            if line:

                self._emit(GremlinEvent(kind="dialogue", text=line, priority=8))

    def notify_cpu(self, pct: float) -> None:

        if pct >= 85:

            self._emit(GremlinEvent(kind="dialogue", text=random.choice(HIGH_CPU_TAUNTS), priority=5))

    def notify_ram(self) -> None:

        self._emit(GremlinEvent(kind="dialogue", text=random.choice(HIGH_RAM_TAUNTS), priority=5))

    def notify_system_notification(self) -> None:

        """Called externally when a desktop notification is detected."""

        if self._notif_cooldown > 0:

            return

        self._emit(GremlinEvent(kind="dialogue",

                                text=random.choice(NOTIFICATION_REACTIONS), priority=3))

        self._notif_cooldown = 30.0

    def notify_typing(self, chars_typed: int, delta_seconds: float) -> None:

        """Called from main with keypress count and elapsed time."""

        if delta_seconds <= 0:

            return

        cps = chars_typed / delta_seconds

        self._typing_cps = self._typing_cps * 0.7 + cps * 0.3

        self._typing_last_active = time.time()

        self._was_typing = True

        self._boredom_seconds = 0.0

        self._idle_seconds = 0.0

        if self._typing_cooldown > 0:

            return

        if self._typing_cps > 6:

            line = random.choice(FAST_TYPING_LINES)

            self._emit_dialogue(line, cooldown=25.0, priority=2)

            self._typing_cooldown = 30.0

        elif self._typing_cps < 1 and self._typing_cps > 0.1:

            line = random.choice(SLOW_TYPING_LINES)

            self._emit_dialogue(line, cooldown=30.0, priority=1)

            self._typing_cooldown = 40.0

    def notify_typing_stopped(self) -> None:

        if self._was_typing and self._typing_cooldown <= 0:

            self._was_typing = False

            if random.random() < 0.25:

                self._emit_dialogue(random.choice(STOPPED_TYPING_LINES), cooldown=20.0, priority=1)

    def notify_clone_spawned(self, total_clones: int) -> None:

        self._clone_count = total_clones

        if total_clones == 2:

            line = random.choice(CLONE_CRISIS_LINES)

        else:

            line = random.choice(MANY_CLONES_LINES)

        self._emit(GremlinEvent(kind="dialogue", text=line, priority=6))

    def notify_source_code_opened(self) -> None:

        line = random.choice(SOURCE_CODE_LINES)

        self._emit(GremlinEvent(kind="dialogue", text=line, priority=5))

    def get_poem_for_category(self, category: Optional[str]) -> str:

        pool = POEM_TEMPLATES.get(category or "generic", POEM_TEMPLATES["generic"])

        return random.choice(pool)

    def get_letter_sequence(self) -> List[str]:

        return random.choice(LETTER_SEQUENCES)

    def _check_wallpaper(self) -> None:

        """Sample the dominant colour of the root window and react."""

        try:

            result = subprocess.run(

                ["xdotool", "getactivewindow"], capture_output=True, timeout=1

            )

            r2 = subprocess.run(

                ["import", "-window", "root", "-resize", "1x1!", "txt:-"],

                capture_output=True, text=True, timeout=3

            )

            if r2.returncode == 0:

                text = r2.stdout

                import re as _re

                m = _re.search(r'rgb\((\d+),(\d+),(\d+)\)', text.replace(' ', ''))

                if m:

                    rv, gv, bv = int(m.group(1)), int(m.group(2)), int(m.group(3))

                    bright = (rv + gv + bv) / 3

                    if bright < 60:

                        key = "dark"

                    elif bright > 200:

                        key = "light"

                    elif bv > rv and bv > gv:

                        key = "blue"

                    elif gv > rv and gv > bv:

                        key = "green"

                    elif rv > gv and rv > bv and rv > 150:

                        key = "red"

                    elif rv > 120 and bv > 120 and gv < 100:

                        key = "purple"

                    else:

                        key = "default"

                    lines = WALLPAPER_COLOR_LINES.get(key, WALLPAPER_COLOR_LINES["default"])

                    QTimer_delay = 8000

                    self._emit(GremlinEvent(kind="dialogue",

                                            text=random.choice(lines), priority=3))

                    return

        except Exception:

            pass

    def save_session_memory(self, last_line: Optional[str] = None) -> None:

        """Call on exit to persist app time and last dialogue."""

        mem = self._memory

        app_time = mem.setdefault("app_time", {})

        for cat, secs in self._session_app_time.items():

            app_time[cat] = app_time.get(cat, 0) + secs

        if last_line:

            mem["last_line"] = last_line

        save_memory(mem)

    def consume_events(self) -> List[GremlinEvent]:

        evs = list(self.pending_events)

        self.pending_events.clear()

        return evs

    def _emit(self, event: GremlinEvent) -> None:

        self.pending_events.append(event)

    def _emit_dialogue(self, text: str, cooldown: float = 20.0, priority: int = 1) -> None:

        if self._dialogue_cooldown > 0:

            return

        self._emit(GremlinEvent(kind="dialogue", text=text, priority=priority))

        self._dialogue_cooldown = cooldown

        self._idle_seconds = 0.0

    def _check_window_focus(self, delta_seconds: float) -> None:

        window = get_focused_window_name()

        if not window:

            return

        if self._last_category:

            self._category_time_seconds += delta_seconds

            self._session_app_time[self._last_category] = (

                self._session_app_time.get(self._last_category, 0) + delta_seconds

            )

            if self._escalation_cooldown <= 0:

                self._check_escalation()

        if window == self._last_window:

            return

        self._last_window = window

        self._category_time_seconds = 0.0

        self._category_escalation_idx = 0

        title_key = detect_title_match(window)

        if title_key and title_key != self._last_title_key:

            self._last_title_key = title_key

            pool = TITLE_REACTIONS[title_key]

            count = self._title_dialogue_counts.get(title_key, 0)

            line = pool[count % len(pool)]

            self._title_dialogue_counts[title_key] = count + 1

            self._emit_dialogue(line, cooldown=12.0, priority=4)

            return

        cat = detect_category(window)

        if cat and cat != self._last_category:

            self._last_category = cat

            total = self._memory.get("app_time", {}).get(cat, 0)

            mem_comment = get_memory_comment(cat, total)

            if mem_comment and random.random() < 0.4:

                self._emit_dialogue(mem_comment, cooldown=15.0, priority=3)

                return

            pool = DIALOGUES.get(cat, DIALOGUES["generic"])

            count = self._category_dialogue_counts.get(cat, 0)

            line = pool[count % len(pool)]

            self._category_dialogue_counts[cat] = count + 1

            self._emit_dialogue(line, cooldown=15.0, priority=3)

    def _check_escalation(self) -> None:

        cat = self._last_category or "generic"

        escalations = ESCALATION_LINES.get(cat, ESCALATION_LINES["generic"])

        while (self._category_escalation_idx < len(escalations) and

               self._category_time_seconds >= escalations[self._category_escalation_idx][0]):

            line = escalations[self._category_escalation_idx][1]

            self._category_escalation_idx += 1

            self._emit_dialogue(line, cooldown=20.0, priority=2)

            self._escalation_cooldown = 60.0

            break

    def _emit_idle_taunt(self) -> None:

        self._emit_dialogue(random.choice(IDLE_TAUNTS), cooldown=30.0, priority=1)

        self._idle_seconds = 0.0

    def _emit_hw_roast(self) -> None:

        if self._hw_tier == "potato":

            roast = random.choice(POTATO_ROASTS)

        elif self._hw_tier == "beast":

            roast = random.choice(BEAST_PC_JEALOUSY)

        else:

            roast = random.choice([

                "Specs are fine. Not interesting, but fine.",

                "16GB RAM. The responsible choice. Very beige.",

                "Mid-range. Gets the job done without drawing attention to itself.",

                "Your hardware has no strong opinions and neither does it inspire any.",

                "Adequate. The word your build would choose for itself.",

            ])

        self._emit(GremlinEvent(kind="hardware_roast", text=roast, priority=10))

    def _check_resources(self) -> None:

        if not _PSUTIL:

            return

        try:

            if psutil.virtual_memory().percent > 90:

                self.notify_ram()

        except Exception:

            pass

    def _update_mouse_velocity(self, pos: Tuple[int, int], dt: float) -> None:

        if self._last_mouse_pos is not None and dt > 0:

            dx = pos[0] - self._last_mouse_pos[0]

            dy = pos[1] - self._last_mouse_pos[1]

            vel = math.sqrt(dx*dx + dy*dy) / dt

            self._mouse_velocity_history.append(vel)

            if len(self._mouse_velocity_history) > 10:

                self._mouse_velocity_history.pop(0)

            avg = sum(self._mouse_velocity_history) / len(self._mouse_velocity_history)

            if avg > 800 and self._dialogue_cooldown <= 0:

                self._emit_dialogue(random.choice(FRANTIC_MOUSE_TAUNTS), cooldown=20.0)

            elif avg < 5 and self._idle_seconds > 20 and self._dialogue_cooldown <= 0:

                self._emit_dialogue(random.choice(SLOW_MOUSE_TAUNTS), cooldown=40.0)

        self._last_mouse_pos = pos

