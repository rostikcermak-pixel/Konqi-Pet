"""
pet_state.py - Single-source-of-truth emotional state machine for Konqi.

Rules:
  * Exactly one state is active at any time: IDLE / HAPPY / ANGRY / SATISFIED.
  * Non-idle states auto-return to IDLE after a fixed duration so the pet
    cannot get stuck in a permanent mood.
  * Transitions are explicit via .set(); there is no randomness inside this
    module - callers (dialog system, user actions) request a change.
  * All behavior modifiers (movement speed, dialog cooldown) are derived
    from the state via properties - no hidden globals.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Callable, Optional


class PetState(Enum):
    IDLE      = "idle"
    HAPPY     = "happy"
    ANGRY     = "angry"
    SATISFIED = "satisfied"


# Seconds a non-idle state lasts before auto-reverting to IDLE.
_STATE_DURATIONS = {
    PetState.HAPPY:     30.0,
    PetState.ANGRY:     25.0,
    PetState.SATISFIED: 20.0,
}

# Movement speed multiplier applied to the physics walk speed per state.
_SPEED_MULTIPLIERS = {
    PetState.IDLE:      1.0,
    PetState.HAPPY:     1.6,
    PetState.ANGRY:     1.9,
    PetState.SATISFIED: 0.6,
}

# Minimum seconds between interactive dialogs per state, to prevent spam.
_DIALOG_COOLDOWN = {
    PetState.IDLE:      25.0,
    PetState.HAPPY:     20.0,
    PetState.ANGRY:     15.0,
    PetState.SATISFIED: 30.0,
}


class PetStateMachine:
    """
    Owns the pet's emotional state. Designed to be driven from a single
    non-blocking tick in the main event loop.
    """

    def __init__(self,
                 on_change: Optional[Callable[[PetState], None]] = None) -> None:
        self._state: PetState       = PetState.IDLE
        self._entered_at: float     = time.time()
        self._last_dialog_at: float = 0.0
        self._on_change             = on_change

    @property
    def state(self) -> PetState:
        return self._state

    def set(self, new_state: PetState) -> None:
        """Request a state change. Refreshes the duration if already active."""
        if new_state is self._state:
            self._entered_at = time.time()
            return
        self._state      = new_state
        self._entered_at = time.time()
        if self._on_change is not None:
            self._on_change(new_state)

    def tick(self) -> bool:
        """
        Advance the state machine. Returns True if the state changed.
        Safe to call every frame; constant time.
        """
        if self._state is PetState.IDLE:
            return False
        duration = _STATE_DURATIONS.get(self._state, 20.0)
        if time.time() - self._entered_at >= duration:
            self.set(PetState.IDLE)
            return True
        return False

    @property
    def speed_multiplier(self) -> float:
        return _SPEED_MULTIPLIERS[self._state]

    def dialog_ready(self) -> bool:
        """True if enough time has passed since the last dialog to show another."""
        cooldown = _DIALOG_COOLDOWN[self._state]
        return (time.time() - self._last_dialog_at) >= cooldown

    def note_dialog_shown(self) -> None:
        self._last_dialog_at = time.time()
