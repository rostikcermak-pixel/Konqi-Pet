# Flatpak packaging

Files here let you build and run Konqi Pet as a Flatpak.

## Build & install locally

```bash
# One-time: install the KDE runtime + SDK
flatpak install -y flathub org.kde.Platform//6.8 org.kde.Sdk//6.8

# Build and install for your user
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.rostikcermak_pixel.KonqiPet.yaml

# Run it
flatpak run io.github.rostikcermak_pixel.KonqiPet
```

A local `flatpak-builder` build has network access, so the `pip3 install`
step in the manifest resolves dependencies (PyQt6, Pillow, psutil, requests)
straight from PyPI.

## Notes / sandbox limitations

- **App detection** (the dialogue that reacts to your open windows) relies on
  `xdotool` and is best-effort inside the sandbox - the pet still walks,
  climbs, and does chaos events without it.
- **Self-updater** uses `git pull` and is a no-op in the Flatpak; updates come
  through Flatpak instead.
- Config and memory are written to the per-app data dir
  (`~/.var/app/io.github.rostikcermak_pixel.KonqiPet/`).

## Submitting to Flathub

Flathub builds run **offline**, so the `pip3 install` shortcut won't pass
review as-is. Replace the `python-deps` module with pinned, hashed sources:

```bash
# Generates a python3-modules.yaml with sha256-pinned wheels
flatpak-pip-generator PyQt6 Pillow psutil requests
```

Then reference the generated file from the manifest instead of the inline
`pip3 install`. Everything else (app-id, desktop file, AppStream metainfo,
icon, finish-args) already follows Flathub conventions.
