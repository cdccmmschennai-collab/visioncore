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


def safe_folder_name(name: str) -> str:
    """Strip characters that aren't valid in a Windows path segment, and
    collapse anything that would otherwise escape SAVE_ROOT (a bare '..' or
    '.' folder name)."""
    cleaned = _INVALID_CHARS.sub("_", name).strip(" .")
    if not cleaned or cleaned in (".", ".."):
        return "untitled-tag"
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

        folder = os.path.join(SAVE_ROOT, safe_folder_name(tag_folder_raw))
        os.makedirs(folder, exist_ok=True)

        if kind == "template_revision":
            path = next_revision_path(folder)
        else:
            path = os.path.join(folder, _BASE_NAMES[kind])
            if os.path.exists(path):
                # Idempotent by design: a base file, once written, is never
                # overwritten — this is what makes it safe for the frontend
                # to call this on every poll tick without risking data loss.
                self._json(200, {"saved": False, "reason": "already exists", "path": path})
                return

        with open(path, "wb") as f:
            f.write(data)
        self._json(200, {"saved": True, "path": path})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        print(f"[VisionCore Local Helper] {self.address_string()} - {format % args}")


def main() -> None:
    os.makedirs(SAVE_ROOT, exist_ok=True)
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
