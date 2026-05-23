#!/usr/bin/env python3
"""Para-Soul Sync Daemon

Auto-syncs para soul data to Paragate every 10 minutes.
Also pulls from Paragate every 15 minutes for bidirectional sync.
Output written to .para/sync/sync_daemon.log
"""

import subprocess
import time
import sys
import os
from datetime import datetime

SYNC_INTERVAL = 600  # 10 minutes
PULL_INTERVAL = 900  # 15 minutes (pull less often to reduce load)
LOG_FILE = "/mnt/d/边飞/零/.para/sync/sync_daemon.log"

ENV = {
    "PARA_HOME": "/mnt/d/边飞/零/.para",
    "PARA_KEYS_DIR": "/mnt/d/边飞/Paragate/keys/admin",
    "PARAGATE_URL": "http://139.180.154.162",
}

CORE_PY = "/mnt/d/边飞/Paragate/para-soul/core.py"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass  # Don't crash if disk is full

def sync_once():
    """Push full soul to Paragate."""
    env = os.environ.copy()
    env.update(ENV)
    try:
        result = subprocess.run(
            ["python3", CORE_PY, "sync-full"],
            capture_output=True, text=True, timeout=30, env=env
        )
        if "✅" in result.stdout:
            log("✅ Sync-full OK")
        else:
            log(f"❌ Sync-full FAIL: {result.stderr.strip()[:150] or result.stdout.strip()[:150]}")
    except Exception as e:
        log(f"❌ Sync-full ERROR: {e}")


def pull_once():
    """Pull soul from Paragate and merge."""
    env = os.environ.copy()
    env.update(ENV)
    try:
        result = subprocess.run(
            ["python3", CORE_PY, "pull-full"],
            capture_output=True, text=True, timeout=30, env=env
        )
        if "✅" in result.stdout:
            log("✅ Pull-full OK — " + result.stdout.strip().split("\n")[0])
        else:
            log(f"❌ Pull-full FAIL: {result.stderr.strip()[:150] or result.stdout.strip()[:150]}")
    except Exception as e:
        log(f"❌ Pull-full ERROR: {e}")

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log("Daemon started. Sync: 10min, Pull: 15min")
    log(f"PARA_HOME: {ENV['PARA_HOME']}")

    # First run
    sync_once()

    last_pull = 0
    while True:
        for _ in range(int(SYNC_INTERVAL / 10)):
            time.sleep(10)
            elapsed = time.time() - last_pull if last_pull else PULL_INTERVAL
            if elapsed >= PULL_INTERVAL:
                pull_once()
                last_pull = time.time()
        sync_once()

if __name__ == "__main__":
    main()
