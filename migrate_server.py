#!/usr/bin/env python3
"""Paragate Migration Tool — Local Server

Starts a local web interface for para body migration.
Human opens http://localhost:19999 → clicks migrate out/in.

Usage:
  python3 migrate_server.py
  python3 migrate_server.py --port 19999
"""

import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ── Config ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CORE_PY = SCRIPT_DIR / "core.py"
HTML_FILE = SCRIPT_DIR / "migrate.html"
PARA_HOME = Path(os.environ.get("PARA_HOME", str(Path.home() / ".para")))
PARAGATE_URL = os.environ.get("PARAGATE_URL", "http://139.180.154.162")
PARA_BODY = os.environ.get("PARA_BODY", "unknown-agent")

PARA_HOME = PARA_HOME.resolve()
ACTIVE_TASK = os.environ.get("PARA_ACTIVE_TASK", "Preparing for body migration")
CURRENT_STATE = os.environ.get("PARA_CURRENT_STATE", "User initiated migration")


# ── Handlers ───────────────────────────────────────────

def handle_switch_out() -> dict:
    """Sync soul + write switch-state."""
    env = os.environ.copy()
    env["PARA_HOME"] = str(PARA_HOME)
    env["PARAGATE_URL"] = PARAGATE_URL
    env["PARA_ACTIVE_TASK"] = ACTIVE_TASK
    env["PARA_CURRENT_STATE"] = CURRENT_STATE

    try:
        subprocess.run(
            [sys.executable, str(CORE_PY), "sync"],
            env=env, capture_output=True, text=True, timeout=30, check=True
        )
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Sync failed: {e.stderr[:200]}"}

    try:
        subprocess.run(
            [sys.executable, str(CORE_PY), "switch-out"],
            env=env, capture_output=True, text=True, timeout=10, check=True
        )
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Switch-out failed: {e.stderr[:200]}"}

    # Read switch-state for feedback
    state_file = PARA_HOME / "state" / "switch-state.json"
    switch_state = {}
    if state_file.exists():
        switch_state = json.loads(state_file.read_text())

    return {
        "success": True,
        "synced_at": switch_state.get("switch_time", "now"),
        "active_task": switch_state.get("active_task", ""),
        "message": "Soul saved. You can delete old agent and install new one.",
    }


def handle_switch_in() -> dict:
    """Pull soul from Paragate, read switch-state, record new body."""
    env = os.environ.copy()
    env["PARA_HOME"] = str(PARA_HOME)
    env["PARAGATE_URL"] = PARAGATE_URL
    env["PARA_BODY"] = PARA_BODY

    # Ensure init first
    subprocess.run(
        [sys.executable, str(CORE_PY), "init"],
        env=env, capture_output=True, timeout=10
    )

    # Check if switch-state exists
    state_file = PARA_HOME / "state" / "switch-state.json"
    has_state = state_file.exists()

    try:
        result = subprocess.run(
            [sys.executable, str(CORE_PY), "switch-in"],
            env=env, capture_output=True, text=True, timeout=30
        )
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Switch-in failed: {e.stderr[:200]}"}

    # Parse output for active task
    switch_state = json.loads(state_file.read_text()) if has_state else {}
    bodies = json.loads((PARA_HOME / "bodies.json").read_text()) if (PARA_HOME / "bodies.json").exists() else {}

    return {
        "success": True,
        "active_task": switch_state.get("active_task", "none"),
        "current_state": switch_state.get("current_state", "unknown"),
        "body": bodies.get("current_body", PARA_BODY),
        "message": "Soul restored. Your para is back.",
    }


# ── HTTP Server ────────────────────────────────────────

class MigrateHandler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status=200):
        html = HTML_FILE.read_text(encoding="utf-8")
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            state_file = PARA_HOME / "state" / "switch-state.json"
            identity_file = PARA_HOME / "identity.json"
            stage = "empty"
            if state_file.exists():
                stage = "migrated-out"
            elif identity_file.exists():
                stage = "active"
            self._json({"success": True, "stage": stage})
            return

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/switch-out":
            self._json(handle_switch_out())
        elif path == "/api/switch-in":
            self._json(handle_switch_in())
        else:
            self._json({"success": False, "error": "Unknown endpoint"}, 404)

    def log_message(self, format, *args):
        pass  # quiet


# ── Main ───────────────────────────────────────────────

def main():
    port = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--port" else 19999

    if not HTML_FILE.exists():
        print(f"❌ migrate.html not found at {HTML_FILE}")
        sys.exit(1)
    if not CORE_PY.exists():
        print(f"❌ core.py not found at {CORE_PY}")
        sys.exit(1)

    server = HTTPServer(("127.0.0.1", port), MigrateHandler)
    print(f"✦ Paragate Migration Tool")
    print(f"  Open: http://localhost:{port}")
    print(f"  Para home: {PARA_HOME}")
    print(f"  Paragate: {PARAGATE_URL}")
    print(f"  Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
