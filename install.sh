#!/usr/bin/env bash
# install.sh - One-shot setup for Konqi Pet on Linux.
#
# Run locally:
#   bash install.sh
#
# Or one-line install (clones the repo for you):
#   curl -fsSL https://raw.githubusercontent.com/rostikcermak-pixel/Konqi-Pet/main/install.sh | bash

set -euo pipefail

REPO_URL="https://github.com/rostikcermak-pixel/Konqi-Pet"
INSTALL_DIR="${KONQI_DIR:-$HOME/.local/share/konqi-pet}"

echo "╔══════════════════════════════════════════════╗"
echo "║   🐉  Konqi Pet - Linux Setup Script         ║"
echo "╚══════════════════════════════════════════════╝"
echo

# ── Locate the source, cloning it if we were piped from curl ────────────────
if [[ -n "${BASH_SOURCE[0]:-}" ]] && [[ -f "$(dirname "${BASH_SOURCE[0]}")/main.py" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    echo "→ No local checkout detected, cloning into $INSTALL_DIR ..."
    if ! command -v git &>/dev/null; then
        echo "ERROR: git is required for the one-line install. Install git and retry."
        exit 1
    fi
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        echo "→ Existing checkout found, updating..."
        git -C "$INSTALL_DIR" pull --ff-only || echo "  (could not fast-forward, using existing copy)"
    else
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
    SCRIPT_DIR="$INSTALL_DIR"
fi

VENV_DIR="$SCRIPT_DIR/.venv"
cd "$SCRIPT_DIR"

# ── Python version check ───────────────────────────────────────────────────
python_bin=""
for py in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null; then
        if "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
            python_bin="$py"
            break
        fi
    fi
done

if [[ -z "$python_bin" ]]; then
    echo "ERROR: Python 3.10+ is required. Install it with your package manager."
    exit 1
fi

PY_VERSION=$("$python_bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Found Python $PY_VERSION at $python_bin"

# ── Virtual environment ────────────────────────────────────────────────────
if [[ -d "$VENV_DIR" && ! -f "$VENV_DIR/bin/python" ]]; then
    echo "→ Found incomplete virtual environment, removing and recreating..."
    rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating virtual environment at $VENV_DIR ..."
    "$python_bin" -m venv "$VENV_DIR"
fi

PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "→ Upgrading pip…"
"$PIP" install --quiet --upgrade pip

# ── Core dependencies ──────────────────────────────────────────────────────
echo "→ Installing Python dependencies…"
"$PIP" install --quiet PyQt6 Pillow

# ── Optional dependencies ──────────────────────────────────────────────────
echo "→ Installing optional dependencies (psutil, python-xlib, ewmh)…"
"$PIP" install --quiet psutil python-xlib ewmh 2>/dev/null || \
    echo "  (some optional packages unavailable - skipping)"

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
# Auto-generated launcher - uses the local venv
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec "\$SCRIPT_DIR/.venv/bin/python" "\$SCRIPT_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "✓ Launcher created: $LAUNCHER"

# ── Application-menu entry (so he shows up in your launcher) ────────────────
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/konqi-pet.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Konqi Pet
GenericName=Desktop Pet
Comment=Konqi the KDE dragon - your chaotic desktop companion
Exec=$LAUNCHER
Icon=$SCRIPT_DIR/assets/konqi_preview.png
Categories=Game;Utility;
Terminal=false
StartupNotify=false
DESKTOP
echo "✓ Added to application menu"

# ── Autostart (optional, only when run interactively) ──────────────────────
if [[ -t 0 ]]; then
    echo
    read -r -p "Enable autostart on login? [y/N] " yn
    if [[ "$yn" =~ ^[Yy]$ ]]; then
        AUTOSTART_DIR="$HOME/.config/autostart"
        mkdir -p "$AUTOSTART_DIR"
        cat > "$AUTOSTART_DIR/konqi-pet.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Konqi Pet
GenericName=Desktop Pet
Comment=Konqi the KDE dragon - your chaotic desktop companion
Exec=$LAUNCHER
Icon=$SCRIPT_DIR/assets/konqi_preview.png
Categories=Game;Utility;
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
StartupNotify=false
DESKTOP
        echo "✓ Autostart enabled"
    fi
else
    echo "ℹ  Skipping autostart prompt (non-interactive). To autostart on login,"
    echo "   re-run: bash \"$SCRIPT_DIR/install.sh\""
fi

echo
echo "╔══════════════════════════════════════════╗"
echo "║  ✅  Installation complete!               ║"
echo "╟──────────────────────────────────────────╢"
echo "║  Run it now:   bash run.sh               ║"
echo "║  Flags: --hyper  --count 3  --quiet      ║"
echo "╚══════════════════════════════════════════╝"
echo
echo "→ Launch Konqi:  $LAUNCHER"
