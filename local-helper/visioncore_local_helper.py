"""VisionCore Local Helper.

The VisionCore web app runs in a browser and, for most users, on a server
that isn't this PC — neither of those can silently write files to this
machine's C:\ drive. This tiny, dependency-free HTTP server is the piece that
can: it listens on 127.0.0.1 only, and the VisionCore frontend posts the
generated workbooks to it so they land at

    C:\Asset photo data capturing tool\<TAG NUMBER>-<DESCRIPTION>\
        AI Output.xlsx
        Template Output.xlsx
        Template Output Revision 1.xlsx
        Template Output Revision 2.xlsx
        ...

Run it with:  python visioncore_local_helper.py
(or double-click start_helper.bat — see README.md in this folder)

Nothing here talks to the internet. It only accepts requests carrying the
shared token below (must match HELPER_TOKEN in
frontend/src/services/localHelper.ts) and only ever writes inside SAVE_ROOT,
under a sanitised per-tag folder name — never an arbitrary path.
"""
from __future__ import annotations

import json
import os
import re
import socketserver
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

# ── Configuration — override via environment variable if needed ────────────
PORT = int(os.environ.get("VISIONCORE_HELPER_PORT", "5577"))
SAVE_ROOT = os.environ.get("VISIONCORE_SAVE_ROOT", r"C:\Asset photo data capturing tool")
# Must match HELPER_TOKEN in frontend/src/services/localHelper.ts.
SHARED_TOKEN = os.environ.get("VISIONCORE_HELPER_TOKEN", "visioncore-local-helper")

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_REVISION_NAME = re.compile(r"^Template Output Revision (\d+)\.xlsx$", re.IGNORECASE)

_BASE_NAMES = {
    "ai": "AI Output.xlsx",
    "template_base": "Template Output.xlsx",
}


def log(message: str) -> None:
    """Print with an immediate flush — this is the only diagnostic trail a
    failed save leaves, so it must never sit in a stdio buffer if this
    window's output is ever redirected to a log file."""
    print(message, flush=True)


def write_file_atomically(folder: str, path: str, data: bytes) -> None:
    """Write `data` to `path` via a temp file + atomic rename.

    A plain open()/write() can leave a partial file at `path` if the process
    is killed or the disk fills up mid-write. Since a base file's mere
    *existence* is what makes this handler skip re-saving it (see do_POST),
    a partial file from one bad run would otherwise permanently block that
    tag's folder from ever being saved correctly again. os.replace() is
    atomic on Windows (same volume), so `path` only ever shows the complete
    file or doesn't exist at all.
    """
    fd, tmp_path = tempfile.mkstemp(dir=folder, prefix=".tmp-upload-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


_MAX_FOLDER_NAME_LEN = 150  # leaves ample room under Windows' ~260-char MAX_PATH
                            # once SAVE_ROOT and the longest filename we write
                            # ("Template Output Revision NN.xlsx") are added.


def safe_folder_name(name: str) -> str:
    """Strip characters that aren't valid in a Windows path segment, collapse
    anything that would otherwise escape SAVE_ROOT (a bare '..' or '.' folder
    name), and cap the length so an unusually long tag description can't push
    the full path past Windows' MAX_PATH limit."""
    cleaned = _INVALID_CHARS.sub("_", name).strip(" .")
    if not cleaned or cleaned in (".", ".."):
        return "untitled-tag"
    if len(cleaned) > _MAX_FOLDER_NAME_LEN:
        cleaned = cleaned[:_MAX_FOLDER_NAME_LEN].strip(" .") or "untitled-tag"
    return cleaned


def next_revision_path(folder: str) -> str:
    """The next 'Template Output Revision N.xlsx' — never reuses a number
    still present on disk, so a manually deleted revision doesn't get
    silently reused for different content."""
    highest = 0
    if os.path.isdir(folder):
        for entry in os.listdir(folder):
            match = _REVISION_NAME.match(entry)
            if match:
                highest = max(highest, int(match.group(1)))
    return os.path.join(folder, f"Template Output Revision {highest + 1}.xlsx")


class Handler(BaseHTTPRequestHandler):
    server_version = "VisionCoreLocalHelper/1.0"

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-VisionCore-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # The deployed frontend is served over HTTPS (a "public" address space per
        # Chrome's Private Network Access spec), while this helper only answers on
        # loopback (a "private" address space). Chrome's preflight for that
        # combination carries "Access-Control-Request-Private-Network: true" and
        # blocks the real request unless this is echoed back — without it, every
        # save silently fails from the deployed site even with the helper running
        # and reachable. Harmless to send unconditionally: browsers that don't
        # enforce PNA just ignore it.
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's naming convention
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._json(200, {"status": "ok", "save_root": SAVE_ROOT})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/save":
            self._json(404, {"error": "not found"})
            return

        if self.headers.get("X-VisionCore-Token") != SHARED_TOKEN:
            self._json(401, {"error": "invalid or missing token"})
            return

        query = parse_qs(parsed.query)
        tag_folder_raw = unquote((query.get("tag_folder") or [""])[0])
        kind = (query.get("kind") or [""])[0]
        if not tag_folder_raw or kind not in ("ai", "template_base", "template_revision"):
            self._json(400, {"error": "tag_folder and a valid kind are required"})
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        data = self.rfile.read(length) if length else b""
        if not data:
            self._json(400, {"error": "empty request body"})
            return

        log("Starting file extraction save...")
        log(f"Extracted file: kind={kind}, tag={tag_folder_raw}")
        log(f"Target directory: {SAVE_ROOT}")

        folder = os.path.join(SAVE_ROOT, safe_folder_name(tag_folder_raw))
        path = None
        try:
            log("Creating directory if required...")
            os.makedirs(folder, exist_ok=True)
            if not os.access(folder, os.W_OK):
                raise PermissionError(f"No write permission for folder: {folder}")

            if kind == "template_revision":
                path = next_revision_path(folder)
            else:
                path = os.path.join(folder, _BASE_NAMES[kind])
                if os.path.exists(path):
                    # Idempotent by design: a base file, once written, is never
                    # overwritten — this is what makes it safe for the frontend
                    # to call this on every poll tick without risking data loss.
                    log(f"Skipped (already saved): {path}")
                    self._json(200, {"saved": False, "reason": "already exists", "path": path})
                    return

            log(f"Saving file to: {path}")
            write_file_atomically(folder, path, data)
            log(f"File saved successfully: {path}")
            self._json(200, {"saved": True, "path": path})
        except Exception as exc:
            log("File save failed")
            log(f"Source: kind={kind}, tag={tag_folder_raw}")
            log(f"Destination: {path or folder}")
            log(f"Error: {exc}")
            self._json(500, {"error": str(exc), "path": path or folder})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        print(f"[VisionCore Local Helper] {self.address_string()} - {format % args}")


def main() -> None:
    try:
        os.makedirs(SAVE_ROOT, exist_ok=True)
        if not os.access(SAVE_ROOT, os.W_OK):
            raise PermissionError(f"No write permission for: {SAVE_ROOT}")
    except OSError as exc:
        log(f"Could not prepare save folder '{SAVE_ROOT}': {exc}")
        log("Set VISIONCORE_SAVE_ROOT to a folder this Windows account can write to, then retry.")
        sys.exit(1)

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"VisionCore Local Helper listening on http://127.0.0.1:{PORT}")
        print(f"Saving workbooks under: {SAVE_ROOT}")
        print("Leave this window open while using VisionCore. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
