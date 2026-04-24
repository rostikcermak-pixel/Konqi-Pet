"""
animation.py – Animation state machine for Konqi Shimeji.

States added: LOOK_AROUND, WAVE
Behaviour tuning:
  - Walk → Idle transition is gradual (low 5% chance per loop)
  - Idle immediately picks next action via _pick_idle_variant
  - Sleep is rare (4%) and capped at 3s
  - look_around / wave are new short idle variants (~8% each)
"""

from __future__ import annotations

import random

from enum import Enum, auto

from typing import Dict, List, Optional, Callable

from PIL import Image

class State(Enum):

    WALK_RIGHT   = auto()

    WALK_LEFT    = auto()

    IDLE         = auto()

    SLEEP        = auto()

    CLIMB_RIGHT  = auto()

    CLIMB_LEFT   = auto()

    FALL         = auto()

    DRAG         = auto()

    FLY          = auto()

    STRETCH      = auto()

    LOOK_AROUND  = auto()

    WAVE         = auto()

FRAME_DURATIONS: Dict[State, int] = {

    State.WALK_RIGHT:   3,

    State.WALK_LEFT:    3,

    State.IDLE:         7,

    State.SLEEP:        12,

    State.CLIMB_RIGHT:  3,

    State.CLIMB_LEFT:   3,

    State.FALL:         2,

    State.DRAG:         2,

    State.FLY:          5,

    State.STRETCH:      9,

    State.LOOK_AROUND:  8,

    State.WAVE:         6,

}

IDLE_MIN_TICKS        = 30

SLEEP_MIN_TICKS       = 180

WALK_MIN_TICKS        = 120

FLY_MIN_TICKS         = 90

STRETCH_MIN_TICKS     = 80

LOOK_AROUND_MIN_TICKS = 60

WAVE_MIN_TICKS        = 50

class AnimationController:

    def __init__(

        self,

        animations: Dict[str, List[Image.Image]],

        fps: int = 60,

        behavior_mode: str = "calm",

        on_state_change: Optional[Callable[[State], None]] = None,

    ) -> None:

        self._anims     = animations

        self._fps       = fps

        self._mode      = behavior_mode

        self._on_change = on_state_change

        self._state: State         = State.IDLE

        self._frame_idx: int       = 0

        self._frame_tick: int      = 0

        self._state_ticks: int     = 0

        self._queued_state: Optional[State] = None

        self.speed: float = 1.0

        self.current_image: Image.Image = self._frames()[0]

    @property

    def state(self) -> State:

        return self._state

    _VOLUNTARY_PAUSE = frozenset({

        State.SLEEP, State.STRETCH, State.FLY,

        State.LOOK_AROUND, State.WAVE,

    })

    def set_state(self, new_state: State, force: bool = False) -> None:

        if new_state == self._state and not force:

            return

        if self._state == State.DRAG and not force:

            self._queued_state = new_state

            return

        if not force and self._state in self._VOLUNTARY_PAUSE:

            return

        self._enter_state(new_state)

    def set_behavior_mode(self, mode: str) -> None:

        self._mode = mode

    def tick(self) -> bool:

        changed = False

        self._state_ticks += 1

        self._frame_tick  += 1

        duration = max(1, int(FRAME_DURATIONS[self._state] / self.speed))

        if self._frame_tick >= duration:

            self._frame_tick = 0

            frames = self._frames()

            self._frame_idx = (self._frame_idx + 1) % len(frames)

            self.current_image = frames[self._frame_idx]

            changed = True

            if self._frame_idx == 0:

                self._consider_transition()

        return changed

    def begin_drag(self) -> None:

        self._enter_state(State.DRAG, force=True)

    def end_drag(self) -> None:

        self._enter_state(State.FALL, force=True)

    def _frames(self) -> List[Image.Image]:

        key_map = {

            State.WALK_RIGHT:  "walk_right",

            State.WALK_LEFT:   "walk_left",

            State.IDLE:        "idle",

            State.SLEEP:       "sleep",

            State.CLIMB_RIGHT: "climb_right",

            State.CLIMB_LEFT:  "climb_left",

            State.FALL:        "fall",

            State.DRAG:        "drag",

            State.FLY:         "fly",

            State.STRETCH:     "stretch",

            State.LOOK_AROUND: "look_around",

            State.WAVE:        "wave",

        }

        key = key_map.get(self._state, "idle")

        return self._anims.get(key, self._anims.get("idle", [Image.new("RGBA", (96,96))]))

    def _enter_state(self, new_state: State, force: bool = False) -> None:

        old = self._state

        self._state        = new_state

        self._frame_idx    = 0

        self._frame_tick   = 0

        self._state_ticks  = 0

        self._queued_state = None

        frames = self._frames()

        self.current_image = frames[0] if frames else self.current_image

        if self._on_change and old != new_state:

            self._on_change(new_state)

    def _consider_transition(self) -> None:

        st    = self._state

        ticks = self._state_ticks

        if self._queued_state is not None:

            self._enter_state(self._queued_state)

            return

        if st in (State.FALL, State.DRAG, State.CLIMB_RIGHT, State.CLIMB_LEFT):

            return

        if st in (State.WALK_RIGHT, State.WALK_LEFT):

            if ticks < WALK_MIN_TICKS:

                return

            if random.random() < 0.06:

                self._enter_state(State.IDLE)

            return

        if st == State.SLEEP:

            if ticks >= SLEEP_MIN_TICKS:

                self._enter_state(State.IDLE)

            return

        if st == State.FLY:

            if ticks >= FLY_MIN_TICKS:

                self._enter_state(State.IDLE)

            return

        if st == State.STRETCH:

            if ticks >= STRETCH_MIN_TICKS:

                self._enter_state(State.IDLE)

            return

        if st == State.LOOK_AROUND:

            if ticks >= LOOK_AROUND_MIN_TICKS:

                self._enter_state(State.IDLE)

            return

        if st == State.WAVE:

            if ticks >= WAVE_MIN_TICKS:

                self._enter_state(State.IDLE)

            return

        if st == State.IDLE:

            if ticks >= IDLE_MIN_TICKS:

                self._pick_idle_variant()

    def _pick_idle_variant(self) -> None:

        """
        Weighted random next action.
        Walk dominates (~75% combined) so character is mostly in motion.
        Short expressive poses (look, wave, stretch) add variety without
        long freezes. Sleep is rare. Re-idle almost never chosen.
        """

        if self._mode == "hyper":

            choices = [

                (State.WALK_RIGHT,  45),

                (State.WALK_LEFT,   45),

                (State.WAVE,         5),

                (State.FLY,          3),

                (State.LOOK_AROUND,  1),

                (State.IDLE,         1),

            ]

        else:

            choices = [

                (State.WALK_RIGHT,  38),

                (State.WALK_LEFT,   38),

                (State.LOOK_AROUND,  8),

                (State.WAVE,         7),

                (State.STRETCH,      5),

                (State.SLEEP,        3),

                (State.FLY,          1),

            ]

        states, weights = zip(*choices)

        chosen = random.choices(states, weights=weights, k=1)[0]

        self._enter_state(chosen)

