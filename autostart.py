"""
autostart.py – Manage the XDG autostart .desktop entry for Konqi Shimeji.

Works on any XDG-compliant desktop (KDE, GNOME, XFCE, etc.).
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

AUTOSTART_DIR  = Path.home() / ".config" / "autostart"
DESKTOP_FILE   = AUTOSTART_DIR / "konqi-shimeji.desktop"
MAIN_SCRIPT    = Path(__file__).parent / "main.py"


_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=Konqi Shimeji
GenericName=Desktop Pet
Comment=Konqi the KDE dragon – your interactive desktop companion
Exec=python3 {exec_path}
Icon=konqueror
Categories=Game;Utility;
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
StartupNotify=false
"""


def enable() -> bool:
    """Create the autostart .desktop entry.  Returns True on success."""
    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        content = _TEMPLATE.format(exec_path=MAIN_SCRIPT.resolve())
        DESKTOP_FILE.write_text(content, encoding="utf-8")
        DESKTOP_FILE.chmod(0o755)
        log.info("Autostart enabled: %s", DESKTOP_FILE)
        return True
    except OSError as exc:
        log.error("Could not write autostart file: %s", exc)
        return False


def disable() -> bool:
    """Remove the autostart .desktop entry.  Returns True on success."""
    try:
        if DESKTOP_FILE.exists():
            DESKTOP_FILE.unlink()
            log.info("Autostart disabled (removed %s)", DESKTOP_FILE)
        return True
    except OSError as exc:
        log.error("Could not remove autostart file: %s", exc)
        return False


def is_enabled() -> bool:
    """Return True if the autostart entry currently exists."""
    return DESKTOP_FILE.exists()


def toggle() -> bool:
    """Toggle autostart.  Returns the new state (True = enabled)."""
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True
