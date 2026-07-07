from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import webview
from webview.menu import Menu, MenuAction, MenuSeparator


DEFAULT_URL = "https://racknerd-31fcf0d.tail38b5b3.ts.net:8092"
APP_NAME = "NirvNotes"
WEBVIEW_PROFILE = "WebView2"
ALLOWED_EXTENSIONS = {".md", ".txt", ".cfg", ".ini"}
TEXT_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".cfg": "text/plain",
    ".ini": "text/plain",
}


class NativeFileStore:
    def __init__(self) -> None:
        self._paths: dict[str, Path] = {}
        self._encodings: dict[str, str] = {}

    def payloads_for_paths(self, paths: list[str]) -> list[dict[str, Any]]:
        payloads = []
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            if not self._is_allowed(path):
                continue

            payload = self._payload_for_path(path)
            if payload:
                payloads.append(payload)
        return payloads

    def save(self, file_id: str, content: str) -> dict[str, Any]:
        path = self._paths.get(file_id)
        if not path or not self._is_allowed(path):
            raise ValueError("File is not writable from this NirvNotes client.")

        encoding = self._encodings.get(file_id, "utf-8")
        try:
            path.write_text(content, encoding=encoding, newline="")
        except UnicodeEncodeError:
            encoding = "utf-8"
            path.write_text(content, encoding=encoding, newline="")
            self._encodings[file_id] = encoding

        stat = path.stat()
        return {
            "id": file_id,
            "name": path.name,
            "size": stat.st_size,
            "lastModified": int(stat.st_mtime * 1000),
        }

    def _payload_for_path(self, path: Path) -> dict[str, Any] | None:
        try:
            content, encoding = read_text(path)
            stat = path.stat()
        except OSError:
            return None

        file_id = str(path.resolve())
        self._paths[file_id] = path.resolve()
        self._encodings[file_id] = encoding
        extension = path.suffix.lower()
        return {
            "id": file_id,
            "name": path.name,
            "path": str(path),
            "extension": extension.removeprefix("."),
            "type": TEXT_TYPES.get(extension, "text/plain"),
            "size": stat.st_size,
            "lastModified": int(stat.st_mtime * 1000),
            "content": content,
            "writable": os.access(path, os.W_OK),
        }

    def _is_allowed(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS


class NirvNotesApi:
    def __init__(self, file_store: NativeFileStore, launch_paths: list[str]) -> None:
        self._file_store = file_store
        self._pending_launch_files = file_store.payloads_for_paths(launch_paths)
        self.window: webview.Window | None = None

    def consume_launch_files(self) -> list[dict[str, Any]]:
        payloads = self._pending_launch_files
        self._pending_launch_files = []
        return payloads

    def open_local_files(self) -> list[dict[str, Any]]:
        if not self.window:
            return []

        paths = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("Text and Markdown (*.md;*.txt;*.cfg;*.ini)",),
        )
        return self._file_store.payloads_for_paths(list(paths or []))

    def save_native_file(self, file_id: str, content: str) -> dict[str, Any]:
        return self._file_store.save(file_id, content)


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    encodings = (
        ("utf-8-sig", "utf-8")
        if raw.startswith(b"\xef\xbb\xbf")
        else ("utf-8", "cp1252", "latin-1")
    )
    for encoding in encodings:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


def resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates = [
        base_path / relative_path,
        Path(__file__).resolve().parent / relative_path,
        Path(__file__).resolve().parent.parent / relative_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def app_data_dir() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = root / "NirvNotes" / WEBVIEW_PROFILE
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NirvNotes Windows client")
    parser.add_argument("files", nargs="*", help="Optional local files to open")
    parser.add_argument("--url", default=DEFAULT_URL, help="NirvNotes server URL")
    parser.add_argument("--width", type=int, default=430)
    parser.add_argument("--height", type=int, default=960)
    parser.add_argument("--min-width", type=int, default=360)
    parser.add_argument("--min-height", type=int, default=520)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def build_url(base_url: str, files: list[str]) -> str:
    base_url = base_url.rstrip("/") or DEFAULT_URL
    return f"{base_url}/open-file" if files else base_url


def run_js(window: webview.Window, script: str) -> None:
    try:
        window.evaluate_js(script)
    except Exception:
        pass


def open_route(window: webview.Window, base_url: str, route: str) -> None:
    window.load_url(f"{base_url.rstrip('/')}{route}")


def build_menu(window_ref: dict[str, webview.Window], base_url: str) -> list[Menu]:
    def window() -> webview.Window | None:
        return window_ref.get("window")

    def go(route: str) -> None:
        if window():
            open_route(window(), base_url, route)

    def dispatch_open_file_dialog() -> None:
        if window():
            run_js(
                window(),
                "window.dispatchEvent(new CustomEvent('nirvnotes:open-native-file-dialog'))",
            )

    def reload() -> None:
        if window():
            current_url = window().get_current_url() or base_url
            window().load_url(current_url)

    def copy_link() -> None:
        if window():
            run_js(
                window(),
                "navigator.clipboard?.writeText(location.href).catch(() => {})",
            )

    def quit_app() -> None:
        if window():
            window().destroy()

    return [
        Menu(
            APP_NAME,
            [
                MenuAction("New note", lambda: go("/new")),
                MenuAction("All notes", lambda: go("/search?term=*&sort=2")),
                MenuSeparator(),
                MenuAction("Open local file...", dispatch_open_file_dialog),
                MenuSeparator(),
                MenuAction("Reload", reload),
                MenuAction("Exit", quit_app),
            ],
        ),
        Menu(
            "Navigate",
            [
                MenuAction("Home", lambda: go("/")),
                MenuAction("Search", lambda: go("/search?term=*&sort=2")),
                MenuAction("Copy current link", copy_link),
            ],
        ),
    ]


def main() -> None:
    args = parse_args()
    file_store = NativeFileStore()
    api = NirvNotesApi(file_store, args.files)
    start_url = build_url(args.url, args.files)
    window_ref: dict[str, webview.Window] = {}
    menu = build_menu(window_ref, args.url)
    icon_path = resource_path("client/assets/favicon.ico")

    window = webview.create_window(
        APP_NAME,
        start_url,
        js_api=api,
        width=args.width,
        height=args.height,
        min_size=(args.min_width, args.min_height),
        background_color="#20252B",
        text_select=True,
        zoomable=True,
        menu=menu,
    )
    if not window:
        raise RuntimeError("Could not create NirvNotes window.")

    api.window = window
    window_ref["window"] = window
    webview.start(
        gui="edgechromium",
        debug=args.debug,
        private_mode=False,
        storage_path=str(app_data_dir()),
        icon=icon_path if Path(icon_path).exists() else None,
        menu=menu,
    )


if __name__ == "__main__":
    main()
