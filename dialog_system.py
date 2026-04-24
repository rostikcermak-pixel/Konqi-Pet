"""
dialog_system.py - Interactive dialog data and selection.

A dialog has exactly one prompt text and exactly two choices.
Each choice maps directly to a PetState result: idle / happy / angry / satisfied.
This module is pure data + selection logic. No Qt, no threads, no timers.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from pet_state import PetState

# --------------------------------------------------------------------------
# Dialog data
# --------------------------------------------------------------------------
# Each entry: {"text": <prompt>, "choices": [ {"text": ..., "result": ...}, ... ]}
# "result" MUST be one of: "idle", "happy", "angry", "satisfied".

DIALOGS: List[Dict] = [
    {
        "text": "Do you want to feed me?",
        "choices": [
            {"text": "Yes",  "result": "happy"},
            {"text": "No",   "result": "angry"},
        ],
    },
    {
        "text": "I'm tired. Can I take a break?",
        "choices": [
            {"text": "Sure, rest", "result": "satisfied"},
            {"text": "Keep going", "result": "angry"},
        ],
    },
    {
        "text": "Am I doing a good job?",
        "choices": [
            {"text": "You are great", "result": "happy"},
            {"text": "Not really",    "result": "angry"},
        ],
    },
    {
        "text": "Want to play a game?",
        "choices": [
            {"text": "Absolutely",   "result": "happy"},
            {"text": "Maybe later",  "result": "satisfied"},
        ],
    },
    {
        "text": "Should I keep watching you work?",
        "choices": [
            {"text": "Yes, stay",    "result": "satisfied"},
            {"text": "Leave me",     "result": "angry"},
        ],
    },
    {
        "text": "I think you should take a walk.",
        "choices": [
            {"text": "Good idea",    "result": "satisfied"},
            {"text": "Mind your business", "result": "angry"},
        ],
    },
    {
        "text": "Am I your favourite thing on screen?",
        "choices": [
            {"text": "Of course",    "result": "happy"},
            {"text": "Not even close", "result": "angry"},
        ],
    },
    {
        "text": "Can I try climbing the wall?",
        "choices": [
            {"text": "Go for it",   "result": "happy"},
            {"text": "Stay down",   "result": "angry"},
        ],
    },
    {
        "text": "Do you want me to be quiet for a while?",
        "choices": [
            {"text": "Yes please",   "result": "satisfied"},
            {"text": "Keep talking", "result": "happy"},
        ],
    },
    {
        "text": "I have something important to say.",
        "choices": [
            {"text": "I'm listening", "result": "satisfied"},
            {"text": "Not now",       "result": "angry"},
        ],
    },
]

# Reaction lines shown by the pet immediately after a choice is made.
_REACTIONS: Dict[str, List[str]] = {
    "happy":     ["Yes!", "Thank you!", "You are the best.", "I love this."],
    "satisfied": ["Fine.", "Acceptable.", "Okay.", "Noted."],
    "angry":     ["Rude.", "Wrong answer.", "You will regret that.", "Fine. Be that way."],
    "idle":      ["Hm.", "Okay.", "Fine."],
}


# --------------------------------------------------------------------------
# Selection API
# --------------------------------------------------------------------------

class DialogSystem:
    """
    Selects dialogs without repeating the same one back-to-back.
    No persistence, no randomness beyond the selection itself.
    """

    def __init__(self) -> None:
        self._recent: List[int] = []

    def pick(self) -> Dict:
        """Return a random dialog that was not shown in the last few picks."""
        n = len(DIALOGS)
        choices = [i for i in range(n) if i not in self._recent]
        if not choices:
            choices = list(range(n))
        idx = random.choice(choices)
        self._recent.append(idx)
        if len(self._recent) > min(4, n - 1):
            self._recent.pop(0)
        return DIALOGS[idx]

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
