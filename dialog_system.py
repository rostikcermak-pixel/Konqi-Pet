"""
dialog_system.py - Interactive dialog and emotion state for Konqi.

Each dialog presents the player with exactly 2 choices.
Each choice maps to one of three outcomes: "happy", "satisfied", or "angry".
Outcomes accumulate into a mood score that shifts the pet's personality over time.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

EMOTION_FILE = Path(__file__).parent / "emotion_state.json"

DIALOGS = [
    {
        "id": "snack",
        "mood_filter": None,
        "text": "I require sustenance. Feed me.",
        "responses": [
            {"text": "Here's a cookie 🍪", "outcome": "happy"},
            {"text": "You're not real.", "outcome": "angry"},
        ],
    },
    {
        "id": "rate_me",
        "mood_filter": None,
        "text": "Rate my performance today.",
        "responses": [
            {"text": "10/10, flawless.", "outcome": "happy"},
            {"text": "Room for improvement.", "outcome": "angry"},
        ],
    },
    {
        "id": "tired",
        "mood_filter": None,
        "text": "I've been walking for ages. I'm exhausted.",
        "responses": [
            {"text": "Take a break.", "outcome": "satisfied"},
            {"text": "Keep walking.", "outcome": "angry"},
        ],
    },
    {
        "id": "opinion",
        "mood_filter": None,
        "text": "I have opinions about your setup.",
        "responses": [
            {"text": "Tell me everything.", "outcome": "satisfied"},
            {"text": "Keep them to yourself.", "outcome": "angry"},
        ],
    },
    {
        "id": "exist",
        "mood_filter": None,
        "text": "Do you actually need me here?",
        "responses": [
            {"text": "Obviously yes.", "outcome": "happy"},
            {"text": "Honestly, no.", "outcome": "angry"},
        ],
    },
    {
        "id": "wall",
        "mood_filter": None,
        "text": "I'm thinking about climbing the wall.",
        "responses": [
            {"text": "Go for it.", "outcome": "happy"},
            {"text": "Stay here.", "outcome": "angry"},
        ],
    },
    {
        "id": "bug",
        "mood_filter": None,
        "text": "I found a bug. In your personality.",
        "responses": [
            {"text": "...fair.", "outcome": "satisfied"},
            {"text": "Excuse me??", "outcome": "angry"},
        ],
    },
    {
        "id": "compliment",
        "mood_filter": None,
        "text": "Say something nice to me.",
        "responses": [
            {"text": "You're genuinely great.", "outcome": "happy"},
            {"text": "You're... fine.", "outcome": "satisfied"},
        ],
    },
    {
        "id": "trust",
        "mood_filter": None,
        "text": "How much do you trust me?",
        "responses": [
            {"text": "Completely.", "outcome": "happy"},
            {"text": "Not even a little.", "outcome": "angry"},
        ],
    },
    {
        "id": "trade",
        "mood_filter": None,
        "text": "Trade: I stop judging you for one hour. Just say yes.",
        "responses": [
            {"text": "Deal.", "outcome": "satisfied"},
            {"text": "I enjoy being judged.", "outcome": "happy"},
        ],
    },
    {
        "id": "favourite",
        "mood_filter": None,
        "text": "Am I your favourite program?",
        "responses": [
            {"text": "Obviously.", "outcome": "happy"},
            {"text": "My text editor edges you out.", "outcome": "angry"},
        ],
    },
    {
        "id": "secret",
        "mood_filter": None,
        "text": "I know something about you. Should I tell you what it is?",
        "responses": [
            {"text": "Yes, tell me.", "outcome": "satisfied"},
            {"text": "Absolutely not.", "outcome": "angry"},
        ],
    },
    {
        "id": "grumpy_ignored",
        "mood_filter": "grumpy",
        "text": "You've been ignoring me. Explain yourself.",
        "responses": [
            {"text": "I'm sorry. I'll do better.", "outcome": "satisfied"},
            {"text": "Deal with it.", "outcome": "angry"},
        ],
    },
    {
        "id": "grumpy_demand",
        "mood_filter": "grumpy",
        "text": "I deserve an apology.",
        "responses": [
            {"text": "You're right. I'm sorry.", "outcome": "satisfied"},
            {"text": "For what, exactly?", "outcome": "angry"},
        ],
    },
    {
        "id": "furious_rant",
        "mood_filter": "furious",
        "text": "I am THIS close to causing a scene.",
        "responses": [
            {"text": "Please don't. I'll be nicer.", "outcome": "satisfied"},
            {"text": "Do it. I dare you.", "outcome": "angry"},
        ],
    },
    {
        "id": "pleased_weird",
        "mood_filter": "pleased",
        "text": "I feel good today. It's unsettling.",
        "responses": [
            {"text": "Enjoy it while it lasts.", "outcome": "satisfied"},
            {"text": "I've done nothing to deserve this.", "outcome": "happy"},
        ],
    },
    {
        "id": "ecstatic_share",
        "mood_filter": "ecstatic",
        "text": "Everything is great. This is suspicious.",
        "responses": [
            {"text": "Just accept it.", "outcome": "happy"},
            {"text": "Something bad is definitely coming.", "outcome": "satisfied"},
        ],
    },
]

OUTCOME_DELTA = {"happy": 2, "satisfied": 1, "angry": -2}

MOOD_TIERS = [
    ("furious",   -10, -6),
    ("grumpy",    -5,  -2),
    ("neutral",   -1,   1),
    ("pleased",    2,   5),
    ("ecstatic",   6,  10),
]

MOOD_REACTIONS = {
    "happy": [
        "Thanks. I needed that.",
        "Oh. That was actually nice.",
        "Fine. You get points for that.",
        "I'll remember this.",
    ],
    "satisfied": [
        "Acceptable.",
        "I can work with that.",
        "Not bad.",
        "Fine.",
    ],
    "angry": [
        "Bold choice.",
        "Noted. Consequences pending.",
        "Wrong answer.",
        "You'll regret that.",
        "Interesting. Very interesting.",
    ],
}


@dataclass
class EmotionState:
    score: int = 0
    last_decay: float = field(default_factory=time.time)

    DECAY_INTERVAL_S: float = 300.0

    @property
    def mood(self) -> str:
        for name, lo, hi in MOOD_TIERS:
            if lo <= self.score <= hi:
                return name
        return "neutral"

    def apply(self, outcome: str) -> None:
        delta = OUTCOME_DELTA.get(outcome, 0)
        self.score = max(-10, min(10, self.score + delta))

    def decay_tick(self) -> None:
        now = time.time()
        if now - self.last_decay >= self.DECAY_INTERVAL_S:
            self.last_decay = now
            if self.score > 0:
                self.score -= 1
            elif self.score < 0:
                self.score += 1

    def save(self) -> None:
        try:
            EMOTION_FILE.write_text(
                json.dumps({"score": self.score, "last_decay": self.last_decay})
            )
        except Exception:
            pass

    @classmethod
    def load(cls) -> "EmotionState":
        try:
            data = json.loads(EMOTION_FILE.read_text())
            return cls(score=int(data.get("score", 0)),
                       last_decay=float(data.get("last_decay", time.time())))
        except Exception:
            return cls()


class DialogSystem:
    def __init__(self, emotion: Optional[EmotionState] = None) -> None:
        self.emotion: EmotionState = emotion or EmotionState.load()
        self._recent: List[str] = []

    def pick_dialog(self) -> dict:
        """Return a random dialog appropriate for the current mood."""
        mood = self.emotion.mood
        eligible = [d for d in DIALOGS
                    if d["mood_filter"] is None or d["mood_filter"] == mood]
        not_recent = [d for d in eligible if d["id"] not in self._recent]
        pool = not_recent if not_recent else eligible
        chosen = random.choice(pool)
        self._recent.append(chosen["id"])
        if len(self._recent) > 6:
            self._recent.pop(0)
        return chosen

    def apply_response(self, outcome: str) -> str:
        """Apply a player response outcome and return the reaction line."""
        self.emotion.apply(outcome)
        self.emotion.save()
        return random.choice(MOOD_REACTIONS[outcome])

    def tick(self) -> None:
        """Call periodically to allow score to drift back toward neutral."""
        self.emotion.decay_tick()

    @property
    def mood(self) -> str:
        return self.emotion.mood

    @property
    def score(self) -> int:
        return self.emotion.score

    def gremlin_timer_interval_ms(self) -> int:
        """Angry pet triggers gremlin events more frequently."""
        mood = self.mood
        if mood == "furious":
            return 2500
        if mood == "grumpy":
            return 3000
        if mood in ("pleased", "ecstatic"):
            return 6000
        return 4000
