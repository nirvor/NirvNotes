from __future__ import annotations

import argparse
import contextlib
import ctypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

import webview
from webview.menu import Menu, MenuAction, MenuSeparator


DEFAULT_URL = "https://racknerd-31fcf0d.tail38b5b3.ts.net:8092"
APP_NAME = "NirvNotes"
WEBVIEW_PROFILE = "WebView2"
DEFAULT_PROXY_PORT = 31992
WINDOW_STATE_FILE = "window-state.json"
LOG_FILE = "nirvnotes-client.log"
INSTANCE_DIR = "instances"
HANDOFF_TIMEOUT_SECONDS = 1.0
ALLOWED_EXTENSIONS = {".md", ".txt", ".cfg", ".ini"}
TEXT_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".cfg": "text/plain",
    ".ini": "text/plain",
}
HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
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
        self._window: webview.Window | None = None

    def consume_launch_files(self) -> list[dict[str, Any]]:
        payloads = self._pending_launch_files
        self._pending_launch_files = []
        return payloads

    def open_local_files(self) -> list[dict[str, Any]]:
        if not self._window:
            return []

        paths = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("Text and Markdown (*.md;*.txt;*.cfg;*.ini)",),
        )
        return self._file_store.payloads_for_paths(list(paths or []))

    def save_native_file(self, file_id: str, content: str) -> dict[str, Any]:
        return self._file_store.save(file_id, content)

    def open_external_paths(self, paths: list[str], browser_base_url: str) -> int:
        payloads = self._file_store.payloads_for_paths(paths)
        if not payloads:
            return 0

        self._pending_launch_files = payloads
        if self._window:
            timestamp = int(time.time() * 1000)
            route = f"{browser_base_url.rstrip('/')}/open-file?nativeLaunch=1&handoff={timestamp}"
            logging.info("loading external handoff route files=%s", len(payloads))
            self._window.load_url(route)
            show_current_process_window()

        return len(payloads)


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


def local_app_root() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = root / "NirvNotes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging() -> None:
    log_dir = local_app_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / LOG_FILE,
        maxBytes=256_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s"),
    )
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def app_data_dir() -> Path:
    path = local_app_root() / WEBVIEW_PROFILE
    path.mkdir(parents=True, exist_ok=True)
    return path


def instance_dir() -> Path:
    path = local_app_root() / INSTANCE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def window_state_path() -> Path:
    return local_app_root() / WINDOW_STATE_FILE


class WinRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def load_window_state(min_width: int, min_height: int) -> dict[str, Any]:
    try:
        state = json.loads(window_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    try:
        width = max(int(state.get("width", 0)), min_width)
        height = max(int(state.get("height", 0)), min_height)
        x = int(state.get("x"))
        y = int(state.get("y"))
    except (TypeError, ValueError):
        return {}

    if not is_window_state_visible(x, y, width, height):
        return {}

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "maximized": bool(state.get("maximized", False)),
    }


def is_window_state_visible(x: int, y: int, width: int, height: int) -> bool:
    if sys.platform != "win32":
        return True

    try:
        user32 = ctypes.windll.user32
        virtual_left = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        virtual_top = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        virtual_width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        virtual_height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    except Exception:
        return True

    virtual_right = virtual_left + virtual_width
    virtual_bottom = virtual_top + virtual_height
    margin = 80
    return (
        x < virtual_right - margin
        and y < virtual_bottom - margin
        and x + width > virtual_left + margin
        and y + height > virtual_top + margin
    )


def find_current_process_window_rect(
    min_width: int,
    min_height: int,
) -> dict[str, Any] | None:
    if sys.platform != "win32":
        return None

    user32 = ctypes.windll.user32
    current_pid = os.getpid()
    candidates: list[dict[str, Any]] = []

    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd: int, _lparam: int) -> bool:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != current_pid or not user32.IsWindowVisible(hwnd):
            return True

        rect = WinRect()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width < min_width or height < min_height:
            return True

        scale = get_window_coordinate_scale(user32, hwnd)
        candidates.append(
            {
                "x": int(round(rect.left * scale)),
                "y": int(round(rect.top * scale)),
                "width": int(round(width * scale)),
                "height": int(round(height * scale)),
                "maximized": bool(user32.IsZoomed(hwnd)),
                "area": width * height,
            },
        )
        return True

    callback_fn = enum_windows_proc(callback)
    user32.EnumWindows(callback_fn, 0)
    if not candidates:
        return None

    state = max(candidates, key=lambda item: item["area"])
    state.pop("area", None)
    return state


def current_process_has_foreground_window() -> bool:
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:
        return False


def show_current_process_window() -> None:
    if sys.platform != "win32":
        return

    try:
        user32 = ctypes.windll.user32
        current_pid = os.getpid()
        enum_windows_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        target_hwnd = ctypes.c_void_p()

        def callback(hwnd: int, _lparam: int) -> bool:
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == current_pid and user32.IsWindowVisible(hwnd):
                target_hwnd.value = hwnd
                return False
            return True

        callback_fn = enum_windows_proc(callback)
        user32.EnumWindows(callback_fn, 0)
        if not target_hwnd.value:
            return

        user32.ShowWindow(target_hwnd.value, 9)  # SW_RESTORE
        user32.SetForegroundWindow(target_hwnd.value)
    except Exception:
        logging.debug("could not focus NirvNotes window", exc_info=True)


def get_window_coordinate_scale(user32: Any, hwnd: int) -> float:
    try:
        dpi = int(user32.GetDpiForWindow(hwnd))
    except Exception:
        dpi = 96
    return 96 / dpi if dpi > 0 else 1.0


def save_window_state(state: dict[str, Any]) -> None:
    try:
        path = window_state_path()
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except OSError:
        pass


def persist_current_window_state(min_width: int, min_height: int) -> None:
    state = find_current_process_window_rect(min_width, min_height)
    if state:
        save_window_state(state)


def start_window_state_persistence(min_width: int, min_height: int) -> threading.Event:
    stop_event = threading.Event()

    if sys.platform != "win32":
        return stop_event

    def persist_loop() -> None:
        last_state: dict[str, Any] | None = None
        time.sleep(0.25)
        while not stop_event.is_set():
            state = find_current_process_window_rect(min_width, min_height)
            if state and state != last_state:
                save_window_state(state)
                last_state = state
            stop_event.wait(0.25)

    threading.Thread(target=persist_loop, daemon=True).start()
    return stop_event


def register_window_state_events(
    window: webview.Window,
    min_width: int,
    min_height: int,
) -> None:
    def persist() -> None:
        persist_current_window_state(min_width, min_height)

    def persist_soon() -> None:
        timer = threading.Timer(0.2, persist)
        timer.daemon = True
        timer.start()

    window.events.moved += persist_soon
    window.events.resized += persist_soon
    window.events.maximized += persist_soon
    window.events.restored += persist_soon
    window.events.closing += persist
    window.events.closed += persist


class LocalProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address: tuple[str, int], upstream_base_url: str) -> None:
        super().__init__(server_address, LocalProxyHandler)
        self.upstream_base_url = upstream_base_url.rstrip("/")


class LocalProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def do_PUT(self) -> None:
        self._proxy()

    def do_PATCH(self) -> None:
        self._proxy()

    def do_DELETE(self) -> None:
        self._proxy()

    def do_OPTIONS(self) -> None:
        self._proxy()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _proxy(self) -> None:
        upstream_base_url = self.server.upstream_base_url  # type: ignore[attr-defined]
        upstream_url = f"{upstream_base_url}{self.path}"
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length) if content_length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        }

        upstream_request = request.Request(
            upstream_url,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with request.urlopen(upstream_request, timeout=30) as response:
                self._send_upstream_response(response.status, response.headers, response.read())
        except error.HTTPError as response:
            self._send_upstream_response(response.code, response.headers, response.read())
        except Exception as exc:
            payload = f"NirvNotes local proxy could not reach upstream: {exc}".encode(
                "utf-8",
                errors="replace",
            )
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)

    def _send_upstream_response(self, status: int, headers: Any, payload: bytes) -> None:
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in HOP_BY_HOP_HEADERS:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def should_proxy_url(url: str, direct: bool) -> bool:
    if direct:
        return False
    parsed = parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def start_local_proxy(
    upstream_base_url: str,
    preferred_port: int = DEFAULT_PROXY_PORT,
) -> tuple[str, LocalProxyServer]:
    port = preferred_port if preferred_port > 0 else find_free_port()
    try:
        server = LocalProxyServer(("127.0.0.1", port), upstream_base_url)
    except OSError:
        if preferred_port <= 0:
            raise
        port = find_free_port()
        server = LocalProxyServer(("127.0.0.1", port), upstream_base_url)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logging.info("local proxy started port=%s upstream=%s", port, upstream_base_url)
    return f"http://127.0.0.1:{port}", server


class HandoffServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        api: NirvNotesApi,
        browser_base_url: str,
    ) -> None:
        super().__init__(server_address, HandoffHandler)
        self.api = api
        self.browser_base_url = browser_base_url


class HandoffHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        if self.path != "/open-files":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(content_length) if content_length else b"{}"
            payload = json.loads(body.decode("utf-8"))
            paths = payload.get("files") if isinstance(payload, dict) else None
            if not isinstance(paths, list):
                raise ValueError("files must be a list")

            clean_paths = [str(path) for path in paths if isinstance(path, str)]
            opened = self.server.api.open_external_paths(  # type: ignore[attr-defined]
                clean_paths,
                self.server.browser_base_url,  # type: ignore[attr-defined]
            )
            if opened < 1:
                self._send_json(422, {"ok": False, "error": "no_supported_files"})
                return

            self._send_json(200, {"ok": True, "opened": opened})
        except Exception as exc:
            logging.warning("external file handoff failed: %s", exc)
            self._send_json(400, {"ok": False, "error": "bad_request"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)


def start_handoff_server(
    api: NirvNotesApi,
    browser_base_url: str,
) -> tuple[HandoffServer, int]:
    port = find_free_port()
    server = HandoffServer(("127.0.0.1", port), api, browser_base_url)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logging.info("handoff server started port=%s", port)
    return server, port


def start_instance_registration(command_port: int) -> threading.Event:
    stop_event = threading.Event()
    started_at = time.time()
    record_path = instance_dir() / f"{os.getpid()}.json"
    last_active = started_at

    def write_record(seen_at: float, active_at: float) -> None:
        record = {
            "pid": os.getpid(),
            "port": command_port,
            "startedAt": started_at,
            "lastSeen": seen_at,
            "lastActive": active_at,
        }
        tmp_path = record_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        tmp_path.replace(record_path)

    try:
        write_record(started_at, last_active)
    except OSError:
        logging.debug("could not write initial NirvNotes instance record", exc_info=True)

    def registration_loop() -> None:
        nonlocal last_active
        while not stop_event.is_set():
            now = time.time()
            if current_process_has_foreground_window():
                last_active = now
            try:
                write_record(now, last_active)
            except OSError:
                logging.debug("could not write NirvNotes instance record", exc_info=True)
            stop_event.wait(0.75)

        with contextlib.suppress(OSError):
            record_path.unlink()

    threading.Thread(target=registration_loop, daemon=True).start()
    return stop_event


def handoff_files_to_existing_instance(paths: list[str]) -> bool:
    if not paths:
        return False

    records = load_instance_records()
    for record in records:
        port = record.get("port")
        if not isinstance(port, int):
            continue

        payload = json.dumps({"files": paths}).encode("utf-8")
        handoff_request = request.Request(
            f"http://127.0.0.1:{port}/open-files",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(
                handoff_request,
                timeout=HANDOFF_TIMEOUT_SECONDS,
            ) as response:
                if 200 <= response.status < 300:
                    logging.info(
                        "handed off files to pid=%s port=%s count=%s",
                        record.get("pid"),
                        port,
                        len(paths),
                    )
                    return True
        except Exception:
            remove_instance_record(record)

    return False


def load_instance_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    now = time.time()
    for path in instance_dir().glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            with contextlib.suppress(OSError):
                path.unlink()
            continue

        if not isinstance(record, dict) or record.get("pid") == os.getpid():
            continue

        last_seen = float(record.get("lastSeen", 0) or 0)
        if now - last_seen > 20:
            with contextlib.suppress(OSError):
                path.unlink()
            continue

        record["_recordPath"] = str(path)
        records.append(record)

    records.sort(
        key=lambda item: (
            float(item.get("lastActive", 0) or 0),
            float(item.get("lastSeen", 0) or 0),
            float(item.get("startedAt", 0) or 0),
        ),
        reverse=True,
    )
    return records


def remove_instance_record(record: dict[str, Any]) -> None:
    raw_path = record.get("_recordPath")
    if not raw_path:
        return

    with contextlib.suppress(OSError):
        Path(str(raw_path)).unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NirvNotes Windows client")
    parser.add_argument("files", nargs="*", help="Optional local files to open")
    parser.add_argument("--url", default=DEFAULT_URL, help="NirvNotes server URL")
    parser.add_argument("--width", type=int, default=430)
    parser.add_argument("--height", type=int, default=960)
    parser.add_argument("--min-width", type=int, default=360)
    parser.add_argument("--min-height", type=int, default=520)
    parser.add_argument(
        "--proxy-port",
        type=int,
        default=DEFAULT_PROXY_PORT,
        help="Stable local proxy port. Use 0 to request a random free port.",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Load the configured URL directly instead of through the local proxy.",
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--native-menu",
        action="store_true",
        help="Show the pywebview native menu bar.",
    )
    return parser.parse_args()


def build_url(base_url: str, files: list[str]) -> str:
    base_url = base_url.rstrip("/") or DEFAULT_URL
    return f"{base_url}/open-file?nativeLaunch=1" if files else base_url


def startup_html() -> str:
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      html,
      body {
        height: 100%;
        margin: 0;
        background: #20252b;
        color: #f6f8fb;
        font-family: "Segoe UI", system-ui, sans-serif;
      }

      body {
        display: grid;
        place-items: center;
      }

      .loader {
        width: 42px;
        height: 42px;
        border: 3px solid rgba(154, 170, 196, 0.22);
        border-top-color: #8fc7ff;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    </style>
  </head>
  <body>
    <div class="loader" aria-label="Loading NirvNotes"></div>
  </body>
</html>
""".strip()


def load_start_url_after_gui(window: webview.Window, start_url: str) -> None:
    logging.info("webview gui started")
    time.sleep(0.15)
    logging.info("loading start url %s", start_url)
    window.load_url(start_url)


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
    setup_logging()
    logging.info("process start pid=%s argv=%s", os.getpid(), sys.argv[1:])
    args = parse_args()
    if args.files and handoff_files_to_existing_instance(args.files):
        logging.info("process exiting after external file handoff")
        return

    file_store = NativeFileStore()
    api = NirvNotesApi(file_store, args.files)
    base_url = args.url.rstrip("/") or DEFAULT_URL
    proxy_server: LocalProxyServer | None = None
    handoff_server: HandoffServer | None = None
    instance_registration_stop: threading.Event | None = None
    browser_base_url = base_url
    if should_proxy_url(base_url, args.direct):
        browser_base_url, proxy_server = start_local_proxy(base_url, args.proxy_port)

    start_url = build_url(browser_base_url, args.files)
    logging.info("start url prepared %s", start_url)
    window_ref: dict[str, webview.Window] = {}
    menu = build_menu(window_ref, browser_base_url) if args.native_menu else []
    icon_path = resource_path("client/assets/favicon.ico")
    saved_window_state = load_window_state(args.min_width, args.min_height)

    window = webview.create_window(
        APP_NAME,
        html=startup_html(),
        js_api=api,
        width=saved_window_state.get("width", args.width),
        height=saved_window_state.get("height", args.height),
        x=saved_window_state.get("x"),
        y=saved_window_state.get("y"),
        min_size=(args.min_width, args.min_height),
        maximized=saved_window_state.get("maximized", False),
        background_color="#20252B",
        text_select=True,
        zoomable=True,
        menu=menu if menu else None,
    )
    if not window:
        raise RuntimeError("Could not create NirvNotes window.")

    logging.info("window created")
    api._window = window
    window_ref["window"] = window
    handoff_server, handoff_port = start_handoff_server(api, browser_base_url)
    instance_registration_stop = start_instance_registration(handoff_port)
    register_window_state_events(window, args.min_width, args.min_height)
    window_state_stop = start_window_state_persistence(args.min_width, args.min_height)
    try:
        webview.start(
            load_start_url_after_gui,
            args=(window, start_url),
            gui="edgechromium",
            debug=args.debug,
            private_mode=False,
            storage_path=str(app_data_dir()),
            icon=icon_path if Path(icon_path).exists() else None,
            menu=menu if menu else None,
        )
    finally:
        logging.info("process shutdown")
        window_state_stop.set()
        if instance_registration_stop:
            instance_registration_stop.set()
        if handoff_server:
            handoff_server.shutdown()
        if proxy_server:
            proxy_server.shutdown()


if __name__ == "__main__":
    main()
