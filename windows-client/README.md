# NirvNotes Windows Client

Small Windows host for the existing NirvNotes web app. Android stays the normal
PWA; this client only replaces the Chrome PWA shell on Windows where Chrome
keeps a hard minimum width.

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File windows-client\run.ps1
```

Open one or more local text files:

```powershell
powershell -ExecutionPolicy Bypass -File windows-client\run.ps1 -Files README.md
```

## Build executable

```powershell
powershell -ExecutionPolicy Bypass -File windows-client\build.ps1
```

The executable is written to:

```text
windows-client\dist\NirvNotes\NirvNotes.exe
```

## Register as Open With app

```powershell
powershell -ExecutionPolicy Bypass -File windows-client\install-file-associations.ps1 -ExePath windows-client\dist\NirvNotes\NirvNotes.exe
```

Windows 11 may still require one manual default-app confirmation for `.md`,
`.txt`, `.cfg`, and `.ini`. That is normal; the script registers the app cleanly
but does not fight Windows UserChoice protection.

## Behavior

- Loads the live NirvNotes VPS URL by default.
- Uses a local loopback proxy by default so WebView2 does not load the Tailnet
  `.ts.net` TLS origin directly.
- Uses persistent WebView2 storage under `%LOCALAPPDATA%\NirvNotes\WebView2`.
- Writes startup diagnostics to `%LOCALAPPDATA%\NirvNotes\logs`.
- Opens `.md`, `.txt`, `.cfg`, and `.ini` from Windows or the native menu.
- Saves edited external files back to their original path when writable.
- Does not import external files into the VPS note folder.
- Supports multiple independent windows. A second app launch gets its own local
  proxy port, and `New Window` opens the current NirvNotes route natively.

## Updates

An installed release checks the NirvNotes server for a newer Windows package.
When one is available, `Update NirvNotes` appears in the normal app menu. The
client downloads the ZIP, verifies its SHA-256 hash and size, backs up the
current installation, replaces it, and restarts. A failed replacement is rolled
back automatically.

The first updater-capable release still needs one normal installer run. Later
releases can use the in-app update action. The server reads the update manifest
and package from `NIRVNOTES_WINDOWS_UPDATE_DIR`.
