"""
sound_engine.py – Sound effects for Konqi Shimeji.

Generates tones in pure Python (no numpy needed), writes them as proper
WAV files to a temp file, and plays via:
  pw-play   (PipeWire — Steam Deck default)
  paplay    (PulseAudio)
  aplay     (ALSA)
  ffplay    (FFmpeg)
in that order of preference.

Falls back silently if nothing is available.
"""

from __future__ import annotations

import array
import logging
import math
import os
import random
import shutil
import struct
import subprocess
import tempfile
import threading
from functools import lru_cache
from typing import Optional

log = logging.getLogger("konqi.sound")

SAMPLE_RATE = 22050  # 22 kHz is plenty for short bleeps/chirps (half the samples!)


# ───────────────────────── WAV encoding ─────────────────────────

def _wav_bytes(samples_float: list[float], rate: int = SAMPLE_RATE) -> bytes:
    """Convert a list of floats [-1..1] to a complete WAV file as bytes."""
    # Use array module for fast bulk conversion instead of struct.pack on a
    # generator of thousands of ints
    pcm = array.array('h', (max(-32768, min(32767, int(s * 32767)))
                            for s in samples_float))
    data_size = len(pcm) * 2
    hdr = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16,
        1, 1, rate, rate * 2, 2, 16,
        b'data', data_size,
    )
    return hdr + pcm.tobytes()


def _env_array(n: int, attack: float = 0.01, release: float = 0.15) -> list[float]:
    """Pre-compute the full envelope as a list — called once per sound, not per sample."""
    if n == 0:
        return []
    inv_n = 1.0 / n
    attack_end = int(attack * n)
    release_start = int((1.0 - release) * n)
    inv_attack = 1.0 / attack if attack > 0 else 1.0
    inv_release = 1.0 / release if release > 0 else 1.0

    env = [0.0] * n
    for i in range(n):
        t = i * inv_n
        if i < attack_end:
            env[i] = t * inv_attack
        elif i >= release_start:
            env[i] = (1.0 - t) * inv_release
        else:
            env[i] = 1.0
    return env


# ───────────────────────── Waveform generators ─────────────────────────

def _sine_wave(freq: float, duration: float, amplitude: float = 0.4) -> list[float]:
    n = int(SAMPLE_RATE * duration)
    env = _env_array(n)
    two_pi_f_over_sr = 2.0 * math.pi * freq / SAMPLE_RATE
    sin = math.sin  # local ref avoids repeated global lookup
    return [amplitude * sin(two_pi_f_over_sr * i) * env[i] for i in range(n)]


def _chirp_wave(f0: float, f1: float, duration: float, amplitude: float = 0.35) -> list[float]:
    n = int(SAMPLE_RATE * duration)
    env = _env_array(n)
    inv_n = 1.0 / n if n else 1.0
    two_pi_over_sr = 2.0 * math.pi / SAMPLE_RATE
    df = f1 - f0
    sin = math.sin

    samples = [0.0] * n
    phase = 0.0
    for i in range(n):
        freq = f0 + df * (i * inv_n)
        phase += two_pi_over_sr * freq
        samples[i] = amplitude * sin(phase) * env[i]
    return samples


def _noise_wave(duration: float, amplitude: float = 0.15) -> list[float]:
    n = int(SAMPLE_RATE * duration)
    env = _env_array(n)
    uniform = random.uniform
    return [amplitude * uniform(-1.0, 1.0) * env[i] for i in range(n)]


def _mix_waves(*waves: list[float]) -> list[float]:
    inv_count = 1.0 / len(waves)
    return [sum(samples) * inv_count for samples in zip(*waves)]


# ───────────────────────── Cached sound generators ─────────────────────────
# Each sound is generated ONCE and the resulting WAV bytes are cached forever.
# These are tiny (a few KB each), so memory is not a concern.

@lru_cache(maxsize=4)
def _footstep(step_parity: int) -> bytes:
    freq = 300 if step_parity == 0 else 250
    return _wav_bytes(_chirp_wave(freq, freq * 0.6, 0.07, 0.20))

@lru_cache(maxsize=1)
def _bounce() -> bytes:
    return _wav_bytes(_chirp_wave(180, 650, 0.14, 0.32))

@lru_cache(maxsize=1)
def _land() -> bytes:
    return _wav_bytes(_chirp_wave(200, 70, 0.09, 0.28))

@lru_cache(maxsize=1)
def _climb_tap() -> bytes:
    return _wav_bytes(_sine_wave(450, 0.055, 0.18))

@lru_cache(maxsize=1)
def _sleep_tone() -> bytes:
    return _wav_bytes(_chirp_wave(320, 140, 0.32, 0.14))

@lru_cache(maxsize=1)
def _drag_squeak() -> bytes:
    return _wav_bytes(_chirp_wave(380, 750, 0.16, 0.30))

@lru_cache(maxsize=1)
def _release_drop() -> bytes:
    return _wav_bytes(_chirp_wave(420, 180, 0.11, 0.22))

@lru_cache(maxsize=1)
def _bubble_pop() -> bytes:
    return _wav_bytes(_chirp_wave(900, 1400, 0.07, 0.24))

# Noise is random so we pre-generate a small pool and pick from it
_SCRIBBLE_POOL: list[bytes] = []

def _scribble() -> bytes:
    if not _SCRIBBLE_POOL:
        # Pre-generate 4 variants — still sounds random enough
        for _ in range(4):
            _SCRIBBLE_POOL.append(_wav_bytes(_noise_wave(0.18, 0.14)))
    return random.choice(_SCRIBBLE_POOL)

@lru_cache(maxsize=1)
def _twin_discord() -> bytes:
    a = _sine_wave(440, 0.22, 0.16)
    b = _sine_wave(466, 0.22, 0.16)
    return _wav_bytes(_mix_waves(a, b))


# ───────────────────────── Player detection ─────────────────────────

def _find_player() -> Optional[str]:
    """Return the first available audio player command."""
    candidates = ["pw-play", "paplay", "aplay", "ffplay", "mpv", "cvlc"]
    for cmd in candidates:
        if shutil.which(cmd):  # no subprocess needed!
            log.info("Sound player: %s", cmd)
            return cmd
    log.warning("No audio player found — sounds disabled")
    return None


_PLAYER: Optional[str] = None
_PLAYER_CHECKED = False


def _get_player() -> Optional[str]:
    global _PLAYER, _PLAYER_CHECKED
    if not _PLAYER_CHECKED:
        _PLAYER = _find_player()
        _PLAYER_CHECKED = True
    return _PLAYER


# ───────────────────────── Playback ─────────────────────────

# Build the command list once per player, not once per play call
_CMD_BUILDERS: dict[str, callable] = {
    "pw-play": lambda f: ["pw-play", f],
    "paplay":  lambda f: ["paplay", f],
    "aplay":   lambda f: ["aplay", "-q", f],
    "ffplay":  lambda f: ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", f],
    "mpv":     lambda f: ["mpv", "--no-video", "--really-quiet", f],
    "cvlc":    lambda f: ["cvlc", "--play-and-exit", "--intf", "dummy", f],
}


def _play_wav_async(wav: bytes) -> None:
    """Write WAV to a temp file and play it in a daemon thread."""
    player = _get_player()
    if player is None:
        return

    cmd_builder = _CMD_BUILDERS.get(player)
    if cmd_builder is None:
        return

    def _worker():
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".wav")
            os.write(fd, wav)
            os.close(fd)

            subprocess.run(
                cmd_builder(tmp),
                timeout=3,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            log.debug("Sound play error: %s", exc)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ───────────────────────── Public API ─────────────────────────

class SoundEngine:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._step_idx = 0

    def _play(self, wav: bytes) -> None:
        if self.enabled:
            _play_wav_async(wav)

    def footstep(self) -> None:
        self._play(_footstep(self._step_idx % 2))  # only 2 variants, cache both
        self._step_idx += 1

    def bounce(self)       -> None: self._play(_bounce())
    def land(self)         -> None: self._play(_land())
    def climb_tap(self)    -> None: self._play(_climb_tap())
    def sleep_tone(self)   -> None: self._play(_sleep_tone())
    def drag_squeak(self)  -> None: self._play(_drag_squeak())
    def release_drop(self) -> None: self._play(_release_drop())
    def bubble_pop(self)   -> None: self._play(_bubble_pop())
    def scribble(self)     -> None: self._play(_scribble())
    def twin_discord(self) -> None: self._play(_twin_discord())

    def test(self) -> None:
        """Play a test tone to verify audio is working."""
        log.info("Sound test: player=%s, enabled=%s", _get_player(), self.enabled)
        was = self.enabled
        self.enabled = True
        self._play(_wav_bytes(_chirp_wave(440, 880, 0.3, 0.4)))
        self.enabled = was
