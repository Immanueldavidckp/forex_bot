# MetaTrader 5 on Arch Linux (Wine + mt5linux bridge)

Goal: Linux Python talks to an MT5 terminal running under Wine, through the mt5linux RPyC bridge on
127.0.0.1:18812. No broker login and no trades in this setup.

Everything Windows-side lives in one prefix: `WINEPREFIX=~/.mt5`, `WINEARCH=win64`.
Installers are kept in `~/.cache/mt5-setup/` (outside the repo).

Log started 2026-10-21 on this machine (`uname -r` 7.2.7-arch1-1).

## Step 1 - current state

| check | result |
|---|---|
| `[multilib]` in `/etc/pacman.conf` | enabled (line 94), no edit needed |
| `wine --version` | `wine-11.18` (package `wine 11.18-1`) |
| `wine-mono`, `wine-gecko`, `winetricks` | not installed |
| `~/.mt5` | does not exist |
| Linux Python | 3.14.7 (`/usr/bin/python3`), `venv` module available |
| display | Wayland session, XWayland on `DISPLAY=:1` (Wine GUI windows will show) |

## Installer downloads (no sudo)

```bash
mkdir -p ~/.cache/mt5-setup/mt5 ~/.cache/mt5-setup/python
curl -fsSL -o ~/.cache/mt5-setup/mt5/mt5setup.exe \
  https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
curl -fsSL -o ~/.cache/mt5-setup/python/python-3.11.9-amd64.exe \
  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
curl -fsSL -o ~/.cache/mt5-setup/python/python-3.11.9-amd64.exe.asc \
  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe.asc
```

- 3.11.9 is the last Python 3.11 release with a Windows installer (later 3.11.x are source-only).
- `mt5setup.exe`: 23,784,536 bytes, PE32+ x86-64 GUI,
  sha256 `a879492dd9d7b168d0538edd1c0dc5604ca43dc0951825b3501818e8b18f4c93`.
  It's a web installer, so this hash changes whenever MetaQuotes updates it. The Authenticode signature was not
  checked (no `osslsigncode` on this machine).
- `python-3.11.9-amd64.exe`: 26,216,840 bytes, md5 `e8dcd502e34932eebcaf1be056d5cbcd`,
  sha256 `5ee42c4eee1e6b4464bb23722f90b45303f79442df63083f05322f1785f5fdde`.
  GPG: **Good signature** from "Steve Dower (Python Release Signing)", primary key fingerprint
  `7ED1 0B65 31D7 C8E1 BC29 6021 FC62 4643 4870 34E5` (python.org's Windows release key). Checked in a
  throwaway keyring:
  ```bash
  export GNUPGHOME=$(mktemp -d)
  gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys FC624643487034E5
  gpg --verify python-3.11.9-amd64.exe.asc python-3.11.9-amd64.exe
  ```
  keys.openpgp.org returns this key without its user ID, so gpg can't use it. Use keyserver.ubuntu.com.

## Step 2 - Wine helper packages (sudo)

[multilib] is already on, so only the missing packages are needed:

```bash
sudo pacman -S --needed wine-mono wine-gecko winetricks
```

Result: installed `wine-mono 11.3.0-1`, `wine-gecko 2.47.4-2`, `winetricks 20260125-2` (run by David).

## Step 3 - create the prefix

```bash
WINEARCH=win64 WINEPREFIX=~/.mt5 wineboot -u
wineserver -w        # wait until the prefix is fully written
```

Result (19 s): `~/.mt5` created, `#arch=win64` in `system.reg`, `wine cmd /c ver` → `Microsoft Windows 10.0.19045`,
Wine Mono present (`drive_c/windows/Microsoft.NET`). No dialogs needed clicking.
Warning seen: `MESA-EGL: warning: egl: failed to create dri2 screen` (NVIDIA GPU 10de:1f9d, no EGL driver
picked). wineboot still exited 0. Watch for chart-drawing problems in the terminal later.

## Step 4 - MetaTrader 5 terminal

```bash
WINEPREFIX=~/.mt5 wine ~/.cache/mt5-setup/mt5/mt5setup.exe
```
