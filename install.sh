#!/usr/bin/env bash
# install.sh – One-shot setup for Konqi Shimeji on Linux
# Usage:  bash install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "╔══════════════════════════════════════════════╗"
echo "║   🐉  Konqi Shimeji – Linux Setup Script     ║"
echo "╚══════════════════════════════════════════════╝"
echo

# ── Python version check ───────────────────────────────────────────────────
python_bin=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null; then
        python_bin="$py"
        break
    fi
done

if [[ -z "$python_bin" ]]; then
    echo "ERROR: Python 3.10+ is required. Install it with your package manager."
    exit 1
fi

PY_VERSION=$("$python_bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Found Python $PY_VERSION at $python_bin"

# ── Virtual environment ────────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating virtual environment at $VENV_DIR …"
    "$python_bin" -m venv "$VENV_DIR"
fi

PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "→ Upgrading pip…"
"$PIP" install --quiet --upgrade pip

# ── Core dependencies ──────────────────────────────────────────────────────
echo "→ Installing Python dependencies…"
"$PIP" install --quiet PyQt6 Pillow requests

# ── Optional dependencies ──────────────────────────────────────────────────
echo "→ Installing optional dependencies (psutil, python-xlib, ewmh)…"
"$PIP" install --quiet psutil python-xlib ewmh 2>/dev/null || \
    echo "  (some optional packages unavailable – skipping)"

# ── System Qt/xcb dependencies reminder ────────────────────────────────────
echo
echo "ℹ  If PyQt6 fails to import with xcb errors, install system Qt libraries:"
echo "   Ubuntu/Debian: sudo apt install libxcb-cursor0 libxcb-icccm4 libxcb-xinerama0"
echo "   Fedora:        sudo dnf install xcb-util-cursor xcb-util-wm"
echo "   Arch:          sudo pacman -S xcb-util-cursor xcb-util-wm"
echo

# ── Launcher script ────────────────────────────────────────────────────────
LAUNCHER="$SCRIPT_DIR/run.sh"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
# Auto-generated launcher – uses the local venv
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec "\$SCRIPT_DIR/.venv/bin/python" "\$SCRIPT_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "✓ Launcher created: $LAUNCHER"

# ── Autostart (optional) ───────────────────────────────────────────────────
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/konqi-shimeji.desktop"

echo
read -r -p "Enable autostart on login? [y/N] " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Konqi Shimeji
GenericName=Desktop Pet
Comment=Konqi the KDE dragon – your interactive desktop companion
Exec=$LAUNCHER
Icon=konqueror
Categories=Game;Utility;
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
StartupNotify=false
DESKTOP
    chmod 755 "$DESKTOP_FILE"
    echo "✓ Autostart enabled: $DESKTOP_FILE"
fi

echo
echo "╔══════════════════════════════════════════╗"
echo "║  ✅  Installation complete!              ║"
echo "╟──────────────────────────────────────────╢"
echo "║  Run with:  bash run.sh                  ║"
echo "║  Or:        $VENV_DIR/bin/python main.py ║"
echo "║                                          ║"
echo "║  Flags:  --hyper   (energetic mode)      ║"
echo "║          --count 3 (spawn 3 Konqis)      ║"
echo "║          --debug   (verbose logging)     ║"
echo "╚══════════════════════════════════════════╝"
