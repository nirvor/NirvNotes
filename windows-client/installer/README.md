# NirvNotes Win11 Installer

This package installs the NirvNotes desktop client for the current Windows user.
It does not need admin rights.

## Quick install

Extract the ZIP, then double-click:

```text
Install-NirvNotes.cmd
```

The installer copies the app to:

```text
%LOCALAPPDATA%\Programs\NirvNotes
```

It also creates Start Menu and Desktop shortcuts, registers NirvNotes as an
Open With app for `.md`, `.txt`, `.cfg`, and `.ini`, and adds a normal Windows
uninstaller entry.

This installer is required once for the updater-capable client. Future releases
appear as `Update NirvNotes` in the app menu and install without extracting a
new installer package manually.

## Cloud/backend behavior

The desktop app uses the live RackNerd NirvNotes endpoint by default:

```text
https://racknerd-31fcf0d.tail38b5b3.ts.net:8092
```

So on a fresh Win11 Mini-PC or laptop, make sure Tailscale is installed and
logged in. The installer performs a small Tailscale/VPS check but does not fail
hard when the machine is offline.

## Command-line install

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-NirvNotes.ps1
```

Useful options:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-NirvNotes.ps1 -NoLaunch
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-NirvNotes.ps1 -NoStartMenuShortcut
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-NirvNotes.ps1 -NoDesktopShortcut
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-NirvNotes.ps1 -SkipConnectivityCheck
```

## Uninstall

Use Windows Settings > Apps > Installed apps > NirvNotes, or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\NirvNotes\Uninstall-NirvNotes.ps1"
```

Uninstall keeps WebView2/login data by default. Use `-RemoveUserData` if you
want to remove the local browser profile too.
