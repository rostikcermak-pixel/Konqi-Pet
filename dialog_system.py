"""
dialog_system.py - Interactive dialog data and selection.

One organised list of dialogs covering: wellbeing, opinions, challenges,
PC knowledge, personal questions, and meta/playful prompts.
Each entry has exactly two choices that map to a PetState result.
This module is pure data + selection logic. No Qt, no threads, no timers.
"""
from __future__ import annotations

import getpass
import random
from typing import Dict, List, Optional

from pet_state import PetState

_USERNAME: str = getpass.getuser()


def format_text(text: str) -> str:
    return text.replace("{user}", _USERNAME)


DIALOGS: List[Dict] = [

    # ── Wellbeing ─────────────────────────────────────────────────────────────
    {
        "text": "Hey {user}, when did you last drink water?",
        "choices": [
            {"text": "Just now",    "result": "satisfied"},
            {"text": "Hours ago",   "result": "angry"},
        ],
    },
    {
        "text": "Are you sitting up straight, {user}?",
        "choices": [
            {"text": "I am now",    "result": "satisfied"},
            {"text": "Still slouching", "result": "angry"},
        ],
    },
    {
        "text": "Have you taken a break recently, {user}?",
        "choices": [
            {"text": "Yes, I stepped away", "result": "satisfied"},
            {"text": "Not today",            "result": "angry"},
        ],
    },
    {
        "text": "Are you getting enough sleep, {user}?",
        "choices": [
            {"text": "Yes, well-rested",  "result": "happy"},
            {"text": "Definitely not",    "result": "angry"},
        ],
    },
    {
        "text": "Did you eat something proper today, {user}?",
        "choices": [
            {"text": "Yes, actual food", "result": "happy"},
            {"text": "Just coffee",      "result": "angry"},
        ],
    },
    {
        "text": "How's your stress level today, {user}?",
        "choices": [
            {"text": "Fine, under control", "result": "satisfied"},
            {"text": "Through the roof",    "result": "angry"},
        ],
    },

    # ── Opinions & Debates ────────────────────────────────────────────────────
    {
        "text": "Tabs or spaces, {user}?",
        "choices": [
            {"text": "Tabs, obviously",  "result": "happy"},
            {"text": "Spaces, clearly",  "result": "angry"},
        ],
    },
    {
        "text": "Dark mode or light mode?",
        "choices": [
            {"text": "Dark, always",   "result": "happy"},
            {"text": "Light mode",     "result": "angry"},
        ],
    },
    {
        "text": "Vim or something else?",
        "choices": [
            {"text": "Vim, obviously", "result": "happy"},
            {"text": "Anything else",  "result": "angry"},
        ],
    },
    {
        "text": "Linux was the right choice, wasn't it, {user}?",
        "choices": [
            {"text": "Obviously yes",    "result": "happy"},
            {"text": "I had no choice",  "result": "angry"},
        ],
    },
    {
        "text": "Rolling release or stable, {user}?",
        "choices": [
            {"text": "Rolling, live dangerously", "result": "happy"},
            {"text": "Stable, I value sleep",     "result": "satisfied"},
        ],
    },
    {
        "text": "Is a hotdog a sandwich, {user}?",
        "choices": [
            {"text": "Yes, obviously",   "result": "happy"},
            {"text": "Absolutely not",   "result": "angry"},
        ],
    },
    {
        "text": "Git pull or git fetch then merge, {user}?",
        "choices": [
            {"text": "Fetch then merge", "result": "happy"},
            {"text": "Just pull, yolo",  "result": "angry"},
        ],
    },

    # ── Challenges ────────────────────────────────────────────────────────────
    {
        "text": "Can you name the shortcut for undo without thinking?",
        "choices": [
            {"text": "Ctrl+Z, trivial",  "result": "happy"},
            {"text": "Had to think",     "result": "satisfied"},
        ],
    },
    {
        "text": "How many browser tabs do you have open right now, {user}?",
        "choices": [
            {"text": "Under 10, healthy", "result": "happy"},
            {"text": "Don't judge me",    "result": "angry"},
        ],
    },
    {
        "text": "Have you saved your work recently, {user}?",
        "choices": [
            {"text": "Auto-save is on",  "result": "satisfied"},
            {"text": "Oh no...",         "result": "angry"},
        ],
    },
    {
        "text": "Is your code currently compiling, {user}?",
        "choices": [
            {"text": "Yes, it builds",      "result": "happy"},
            {"text": "There are... issues", "result": "angry"},
        ],
    },

    # ── Real PC Knowledge ─────────────────────────────────────────────────────
    {
        "text": "Did you know Ctrl+R in bash searches your command history, {user}?",
        "choices": [
            {"text": "Yes, I use it",      "result": "satisfied"},
            {"text": "Oh, I didn't know",  "result": "happy"},
        ],
    },
    {
        "text": "Do you back up your files regularly, {user}?",
        "choices": [
            {"text": "3-2-1 rule, always", "result": "happy"},
            {"text": "I should do that",   "result": "angry"},
        ],
    },
    {
        "text": "Do you use a password manager, {user}?",
        "choices": [
            {"text": "Yes, KeePassXC",      "result": "happy"},
            {"text": "My brain is my vault", "result": "angry"},
        ],
    },
    {
        "text": "Do you check 'man' pages when stuck, or just Google, {user}?",
        "choices": [
            {"text": "man first, always",   "result": "happy"},
            {"text": "Stack Overflow wins",  "result": "angry"},
        ],
    },
    {
        "text": "Have you set up SSH keys instead of typing passwords, {user}?",
        "choices": [
            {"text": "Yes, long ago",        "result": "satisfied"},
            {"text": "Not yet, I should",    "result": "angry"},
        ],
    },
    {
        "text": "Do you use tmux or screen for persistent sessions, {user}?",
        "choices": [
            {"text": "tmux, obviously",      "result": "happy"},
            {"text": "What's the point",     "result": "angry"},
        ],
    },
    {
        "text": "Do you use aliases in your shell config, {user}?",
        "choices": [
            {"text": "Dozens of them",       "result": "happy"},
            {"text": "I type everything out", "result": "angry"},
        ],
    },

    # ── Personal / Meta ───────────────────────────────────────────────────────
    {
        "text": "Coffee or tea, {user}?",
        "choices": [
            {"text": "Coffee, life depends",  "result": "happy"},
            {"text": "Tea, civilised choice", "result": "satisfied"},
        ],
    },
    {
        "text": "What's your favourite programming language, {user}?",
        "choices": [
            {"text": "Python, obviously",       "result": "happy"},
            {"text": "Something compiled",      "result": "satisfied"},
        ],
    },
    {
        "text": "Am I your favourite thing on screen, {user}?",
        "choices": [
            {"text": "Of course, Konqi!",  "result": "happy"},
            {"text": "There are others...", "result": "angry"},
        ],
    },
    {
        "text": "Should I wake you if you fall asleep at your desk, {user}?",
        "choices": [
            {"text": "Please, yes",     "result": "happy"},
            {"text": "Let me sleep",    "result": "satisfied"},
        ],
    },
    {
        "text": "I've been watching you all day, {user}. Any regrets?",
        "choices": [
            {"text": "Not really",          "result": "satisfied"},
            {"text": "Several, actually",   "result": "angry"},
        ],
    },
    {
        "text": "Do you think you're being productive today, {user}?",
        "choices": [
            {"text": "Actually, yes",       "result": "happy"},
            {"text": "That's a strong word", "result": "angry"},
        ],
    },
    {
        "text": "What's more dangerous: merge conflicts or segfaults, {user}?",
        "choices": [
            {"text": "Merge conflicts, clearly", "result": "angry"},
            {"text": "Segfaults, no contest",    "result": "angry"},
        ],
    },
    {
        "text": "If you could delete one folder forever, what would it be?",
        "choices": [
            {"text": "node_modules, obviously", "result": "happy"},
            {"text": "__pycache__, same energy", "result": "satisfied"},
        ],
    },

    # ── Games ─────────────────────────────────────────────────────────────────
    {
        "text": "Want to play a game, {user}?",
        "choices": [
            {"text": "Absolutely, let's go", "result": "happy"},
            {"text": "Maybe later",          "result": "satisfied"},
        ],
    },
    {
        "text": "How about a round of tic-tac-toe, {user}?",
        "choices": [
            {"text": "Challenge accepted",  "result": "happy"},
            {"text": "I'll pass",           "result": "satisfied"},
        ],
    },
    {
        "text": "Do you think you could beat me at tic-tac-toe, {user}?",
        "choices": [
            {"text": "Easily, watch me",     "result": "happy"},
            {"text": "I have no confidence", "result": "angry"},
        ],
    },

    # ── Konqi-specific ────────────────────────────────────────────────────────
    {
        "text": "Can I try climbing the wall?",
        "choices": [
            {"text": "Go for it",  "result": "happy"},
            {"text": "Stay down",  "result": "angry"},
        ],
    },
    {
        "text": "Should I keep watching you work, {user}?",
        "choices": [
            {"text": "Yes, stay here",  "result": "satisfied"},
            {"text": "Leave me alone",  "result": "angry"},
        ],
    },
    {
        "text": "I think you should take a break, {user}.",
        "choices": [
            {"text": "Good idea",           "result": "satisfied"},
            {"text": "I'm almost done",     "result": "angry"},
        ],
    },
    {
        "text": "Do you need me to be quiet for a while, {user}?",
        "choices": [
            {"text": "Yes please",   "result": "satisfied"},
            {"text": "Keep talking", "result": "happy"},
        ],
    },
    {
        "text": "I've been here all day, {user}. Do I get overtime?",
        "choices": [
            {"text": "You're salaried",    "result": "angry"},
            {"text": "Fine, extra treats", "result": "happy"},
        ],
    },
]


_REACTIONS: Dict[str, List[str]] = {
    "happy":     ["Yes!", "Thank you!", "You are the best.", "I love this.", "Noted positively."],
    "satisfied": ["Fine.", "Acceptable.", "Okay.", "Noted.", "Reasonable choice."],
    "angry":     ["Rude.", "Wrong answer.", "You will regret that.", "Fine. Be that way.", "Noted. Negatively."],
    "idle":      ["Hm.", "Okay.", "Fine."],
}


class DialogSystem:
    """
    Selects dialogs without repeating the same one back-to-back.
    No persistence, no randomness beyond the selection itself.
    """

    def __init__(self) -> None:
        self._recent: List[int] = []

    def pick(self) -> Dict:
        """Return a random dialog (not shown in the last few picks) with {user} substituted."""
        n = len(DIALOGS)
        choices = [i for i in range(n) if i not in self._recent]
        if not choices:
            choices = list(range(n))
        idx = random.choice(choices)
        self._recent.append(idx)
        if len(self._recent) > min(6, n - 1):
            self._recent.pop(0)
        entry = DIALOGS[idx]
        return {"text": format_text(entry["text"]), "choices": entry["choices"]}

    @staticmethod
    def result_to_state(result: str) -> PetState:
        """Map a choice result string to a PetState enum value."""
        return {
            "idle":      PetState.IDLE,
            "happy":     PetState.HAPPY,
            "angry":     PetState.ANGRY,
            "satisfied": PetState.SATISFIED,
        }.get(result, PetState.IDLE)

    @staticmethod
    def reaction(result: str) -> str:
        """Return a short reaction line for the pet to say after the choice."""
        return random.choice(_REACTIONS.get(result, _REACTIONS["idle"]))
