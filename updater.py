"""
updater.py — GitHub release update checker for Konqi-Pet.

Pure stdlib (urllib + json + subprocess). Designed to be called from a
QThread so the UI stays responsive while the network request is in
flight. apply_update() runs `git pull --ff-only` when the install is
a git checkout; otherwise it returns the release URL so the user can
download manually.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

REPO    = "rostikcermak-pixel/Konqi-Pet"
HERE    = Path(__file__).parent
TIMEOUT = 6

log = logging.getLogger("konqi.updater")


@dataclass
class ReleaseInfo:
    tag: str
    name: str
    url: str
    body: str


def _parse_version(s: str) -> Tuple[int, ...]:
    s = (s or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", s)
    return tuple(int(p) for p in parts) if parts else (0,)


def compare_versions(a: str, b: str) -> int:
    pa, pb = _parse_version(a), _parse_version(b)
    if pa < pb: return -1
    if pa > pb: return 1
    return 0


def is_git_install() -> bool:
    return (HERE / ".git").exists()


def fetch_latest_release() -> Optional[ReleaseInfo]:
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "konqi-pet-updater",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        log.info("Update check failed: %s", exc)
        return None
    except Exception as exc:
        log.info("Update check parse error: %s", exc)
        return None
    return ReleaseInfo(
        tag=data.get("tag_name", "") or "",
        name=data.get("name", "") or "",
        url=data.get("html_url", f"https://github.com/{REPO}/releases/latest"),
        body=(data.get("body") or "")[:500],
    )


def check_for_update(current_version: str) -> Optional[ReleaseInfo]:
    """Return ReleaseInfo only when remote is strictly newer than current."""
    rel = fetch_latest_release()
    if rel is None or not rel.tag:
        return None
    if compare_versions(rel.tag, current_version) > 0:
        return rel
    return None


def _git_pull() -> Tuple[bool, str]:
    try:
        r = subprocess.run(
            ["git", "-C", str(HERE), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, f"git pull failed: {exc}"
    if r.returncode != 0:
        err = (r.stderr or r.stdout).strip().splitlines()
        return False, err[-1] if err else "git pull failed"
    out = (r.stdout or "").strip().splitlines()
    return True, out[-1] if out else "Updated."


def apply_update() -> Tuple[bool, str]:
    """Pull latest if this is a git install. Otherwise advise manual download."""
    if is_git_install():
        return _git_pull()
    return False, (f"Not a git install. Download from "
                   f"https://github.com/{REPO}/releases/latest")
