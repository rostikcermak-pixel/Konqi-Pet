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

import logging
import math
import os
import random
import struct
import subprocess
import tempfile
import threading
from typing import Optional

log = logging.getLogger("konqi.sound")

SAMPLE_RATE = 44100                                       


                                                                             
                
                                                                             

def _wav_bytes(samples_float: list, rate: int = SAMPLE_RATE) -> bytes:
    """Convert a list of floats [-1..1] to a complete WAV file as bytes."""
    n    = len(samples_float)
    pcm  = struct.pack(f'<{n}h', *[max(-32768, min(32767, int(s * 32767)))
                                    for s in samples_float])
                
    data_size = n * 2                
    hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16,
        1,               
        1,                
        rate,
        rate * 2,              
        2,                       
        16,                          
        b'data', data_size)
    return hdr + pcm


def _env(i: int, n: int, attack: float = 0.01, release: float = 0.15) -> float:
    """Simple attack-release envelope."""
    t = i / n
    if t < attack:
        return t / attack
    if t > 1.0 - release:
        return (1.0 - t) / release
    return 1.0


def _sine_wave(freq: float, duration: float, amplitude: float = 0.4) -> list:
    n = int(SAMPLE_RATE * duration)
    return [amplitude * math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * _env(i, n)
            for i in range(n)]


def _chirp_wave(f0: float, f1: float, duration: float, amplitude: float = 0.35) -> list:
    n = int(SAMPLE_RATE * duration)
    phase = 0.0
    samples = []
    for i in range(n):
        t   = i / n
        freq = f0 + (f1 - f0) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        samples.append(amplitude * math.sin(phase) * _env(i, n))
    return samples


def _noise_wave(duration: float, amplitude: float = 0.15) -> list:
    n = int(SAMPLE_RATE * duration)
    return [amplitude * random.uniform(-1.0, 1.0) * _env(i, n) for i in range(n)]


def _mix_waves(*waves: list) -> list:
    n = min(len(w) for w in waves)
    return [sum(w[i] for w in waves) / len(waves) for i in range(n)]


                                                                             
                   
                                                                             

def _footstep(step: int = 0) -> bytes:
    freq = 300 if step % 2 == 0 else 250
    return _wav_bytes(_chirp_wave(freq, freq * 0.6, 0.07, 0.20))

def _bounce() -> bytes:
    return _wav_bytes(_chirp_wave(180, 650, 0.14, 0.32))

def _land() -> bytes:
    return _wav_bytes(_chirp_wave(200, 70, 0.09, 0.28))

def _climb_tap() -> bytes:
    return _wav_bytes(_sine_wave(450, 0.055, 0.18))

def _sleep_tone() -> bytes:
    return _wav_bytes(_chirp_wave(320, 140, 0.32, 0.14))

def _drag_squeak() -> bytes:
    return _wav_bytes(_chirp_wave(380, 750, 0.16, 0.30))

def _release_drop() -> bytes:
    return _wav_bytes(_chirp_wave(420, 180, 0.11, 0.22))

def _bubble_pop() -> bytes:
    return _wav_bytes(_chirp_wave(900, 1400, 0.07, 0.24))

def _scribble() -> bytes:
    return _wav_bytes(_noise_wave(0.18, 0.14))

def _twin_discord() -> bytes:
    a = _sine_wave(440, 0.22, 0.16)
    b = _sine_wave(466, 0.22, 0.16)
    return _wav_bytes(_mix_waves(a, b))


                                                                             
                  
                                                                             

def _find_player() -> Optional[str]:
    """Return the first available audio player command."""
    candidates = ["pw-play", "paplay", "aplay", "ffplay", "mpv", "cvlc"]
    for cmd in candidates:
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                log.info("Sound player: %s", cmd)
                return cmd
        except Exception:
            pass
    log.warning("No audio player found — sounds disabled")
    return None


_PLAYER: Optional[str] = None                                  


def _get_player() -> Optional[str]:
    global _PLAYER
    if _PLAYER is None:
        _PLAYER = _find_player()
    return _PLAYER


                                                                             
                                                                           
                                                                             

def _play_wav_async(wav: bytes) -> None:
    """Write WAV to a temp file and play it in a daemon thread."""
    def _worker():
        player = _get_player()
        if player is None:
            return
        tmp = None
        try:
                                                                          
            fd, tmp = tempfile.mkstemp(suffix=".wav")
            os.write(fd, wav)
            os.close(fd)

            if player == "pw-play":
                cmd = ["pw-play", tmp]
            elif player == "paplay":
                cmd = ["paplay", tmp]
            elif player == "aplay":
                cmd = ["aplay", "-q", tmp]
            elif player == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp]
            elif player == "mpv":
                cmd = ["mpv", "--no-video", "--really-quiet", tmp]
            elif player == "cvlc":
                cmd = ["cvlc", "--play-and-exit", "--intf", "dummy", tmp]
            else:
                return

            subprocess.run(cmd, timeout=3,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except Exception as exc:
            log.debug("Sound play error: %s", exc)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


                                                                             
                    
                                                                             

class SoundEngine:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled   = enabled
        self._step_idx = 0

    def _play(self, wav: bytes) -> None:
        if self.enabled:
            _play_wav_async(wav)

    def footstep(self)    -> None: self._play(_footstep(self._step_idx)); self._step_idx += 1
    def bounce(self)      -> None: self._play(_bounce())
    def land(self)        -> None: self._play(_land())
    def climb_tap(self)   -> None: self._play(_climb_tap())
    def sleep_tone(self)  -> None: self._play(_sleep_tone())
    def drag_squeak(self) -> None: self._play(_drag_squeak())
    def release_drop(self)-> None: self._play(_release_drop())
    def bubble_pop(self)  -> None: self._play(_bubble_pop())
    def scribble(self)    -> None: self._play(_scribble())
    def twin_discord(self)-> None: self._play(_twin_discord())

    def test(self) -> None:
        """Play a test tone to verify audio is working."""
        log.info("Sound test: player=%s, enabled=%s", _get_player(), self.enabled)
        was = self.enabled
        self.enabled = True
        self._play(_chirp_wave(440, 880, 0.3, 0.4).__class__                
                   if False else _wav_bytes(_chirp_wave(440, 880, 0.3, 0.4)))
        self.enabled = was
