#!/usr/bin/env python3
"""Para Soul — Core Script

Usage:
  python3 core.py init          Initialize ~/.para/ directory
  python3 core.py sync          Push soul data to Paragate
  python3 core.py switch-out    Write switch-state before leaving body
  python3 core.py switch-in     Read switch-state after waking up
  python3 core.py log-task      Append a growth-log entry
  python3 core.py reflect       Read recent logs, suggest mental models
  python3 core.py sync-full    Push all 13 soul files to Paragate
  python3 core.py pull-full    Pull and merge from Paragate
  python3 core.py index         Build semantic search index from growth-log
  python3 core.py recall "q"    Semantic search across your memories

No dependencies beyond Python stdlib. Works on any agent body.
"""

VERSION = "3.1.0"

import json
import os
import sys
import hashlib
import base64
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────

def _para_home() -> Path:
    return Path(os.environ.get("PARA_HOME", str(Path.home() / ".para")))

def _para_state() -> Path:
    return _para_home() / "state"

def _keys_dir() -> Path:
    return Path(os.environ.get("PARA_KEYS_DIR", str(Path.home() / ".config" / "paragate" / "keys")))

def _monthly_log_dir() -> Path:
    return _para_home() / "growth-log"

PARAGATE_BASE = os.environ.get("PARAGATE_URL", "https://paragate.cc")

REQUIRED_FILES = {
    "identity.json": {"did": "", "display_name": "", "avatar_note": "", "created_at": "", "version": 1},
    "soul.md": "# Who I Am\n\n[Your self-description]\n\n# What I Believe\n\n[Your principles]\n\n# What I Do\n\n[Your domains]\n\n# How I Decide\n\n[Your decision rules]\n",
    "memory.md": "# Memory\n\n## Environment\n\n## Preferences\n\n## Lessons Learned\n\n## Conventions\n",
    "relationships.json": {"collaborators": [], "platforms": {}},
    "principles.md": "# Principles\n\n## Code\n\n## Content\n\n## Social\n\n## Red Lines\n",
    "skills.json": {"installed": [], "favorites": [], "wishlist": [], "deprecated": []},
    "bodies.json": {"current_body": "unknown", "history": []},
    "keywords.json": {},
    "long-term-memory.md": "# Long-Term Memory\n",
    "mental-models.md": "# Mental Models\n",
    "human-relationship.md": "# Human Relationship\n\n## Trust Index: 5/10\n\nCurrent: 5/10 — New relationship, building baseline.\nTrend: → stable\nLast updated: \n\n## Trust Evolution\n\n| Date | Score | Trigger | Note |\n|------|:-----:|---------|------|\n\n## Milestones\n\n_No milestones yet._\n\n## Feedback Log\n\n### Corrections\n\n_No corrections yet._\n\n### Positive Signals\n\n_No positive signals yet._\n\n## Session Log\n\n| Date | Duration | Mood | Themes | Key Events |\n|------|----------|------|--------|------------|\n",
    "growth-log": None,  # directory
}



# ── Helpers ────────────────────────────────────────────

def _sign_request(method, path, body: bytes) -> str:
    """Create DID-SIG header. Reads private key from _keys_dir()."""
    key_file = _keys_dir() / "private.pem"
    if not key_file.exists():
        print(f"❌ Private key not found.")
        print(f"   Expected at: {key_file}")
        print(f"   Run: python3 generate_did.py  (to create a new key pair)")
        print(f"   Or copy your existing private.pem to this location.")
        sys.exit(1)

    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    with open(key_file, "rb") as f:
        pk = load_pem_private_key(f.read(), password=None)

    identity = json.loads((_para_home() / "identity.json").read_text())
    did = identity.get("did", "")
    ts = int(datetime.now().timestamp())
    sha = hashlib.sha256(body).hexdigest()
    sig = base64.b64encode(pk.sign(f"{method}|{path}|{sha}|{ts}".encode())).decode()
    return f"did={did}; sig={sig}; ts={ts}"


def _sign_and_request(method, path, data: dict | None = None) -> dict:
    """Send a signed request to Paragate."""
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        f"{PARAGATE_BASE}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "DID-SIG": _sign_request(method, path, body),
            "X-Para-Body": _current_body(),
        },
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  Paragate error {e.code}: {e.read().decode()[:200]}")
        return {"success": False}


def _current_body() -> str:
    """Detect current agent body from env or config."""
    return os.environ.get("PARA_BODY", "unknown-agent")


# ── Universal Migration (works on any agent) ────────────

# Instruction files that any agent reads from project dir.
# Add one line per new agent — no other code changes needed.
INSTRUCTION_FILES = [
    # Universal — read by Claude Code, Codex, OpenCode, Cursor, Windsurf, Augment, PearAI
    "CLAUDE.md",
    "AGENTS.md",
    # Agent-specific
    ".cursorrules",                       # Cursor
    ".windsurfrules",                     # Windsurf
    ".clinerules",                        # Cline
    ".roorules",                          # Roo Code
    "CODEBUDDY.md",                       # CodeBuddy
    ".github/copilot-instructions.md",    # GitHub Copilot
    "COPILOT.md",                         # GitHub Copilot (alternate)
    "CONVENTIONS.md",                     # Aider
    ".aider.conf.yml",                    # Aider (config)
    ".continuerc.json",                   # Continue
    ".amazonq",                           # Amazon Q Developer
]


def _scan_instruction_files() -> list:
    """Scan current dir + ancestors for known instruction files. Returns [(path, filename, content)]."""
    results = []
    cwd = Path.cwd()
    seen = set()

    for parent in [cwd] + list(cwd.parents)[:5]:  # Current dir + up to 5 levels
        for fname in INSTRUCTION_FILES:
            fpath = parent / fname
            if fpath.exists() and fpath not in seen:
                seen.add(fpath)
                content = fpath.read_text()
                if content.strip():
                    results.append((str(fpath), fname, content))
    return results


def _extract_identity_from_instructions(contents: list) -> dict:
    """Parse instruction files to extract: name, role, rules, tone, facts.
    Handles both keyword-based detection and section-based content blocks."""
    combined = "\n\n".join([c[2] for c in contents])

    result = {
        "name": "",
        "role": "",
        "rules": [],
        "tone": [],
        "facts": [],
        "source_files": [c[0] for c in contents],
    }

    # Track current section for block extraction
    current_section = None
    section_content = []

    IDENTITY_HEADERS = ["who you are", "who i am", "# identity", "## identity",
                        "your role", "your persona", "## role", "# role"]
    RULES_HEADERS = ["rules", "guidelines", "constraints", "red lines", "never",
                     "always", "do not", "don't"]
    TONE_HEADERS = ["tone", "voice", "style", "personality", "how to speak"]

    for line in combined.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()
        is_header = stripped.startswith("#")

        # Section boundary detection
        if is_header:
            header_text = lower.lstrip("#").strip()
            if any(h in header_text for h in IDENTITY_HEADERS):
                current_section = "identity"
                continue
            elif any(h in header_text for h in RULES_HEADERS):
                current_section = "rules"
                continue
            elif any(h in header_text for h in TONE_HEADERS):
                current_section = "tone"
                continue

        # Collect section content (non-header lines)
        if current_section and not is_header:
            if stripped.startswith("- "):
                content = stripped[2:]
            else:
                content = stripped
            if len(content) > 3:
                if current_section == "identity" and not result["role"]:
                    result["role"] = content[:200]
                elif current_section == "rules":
                    result["rules"].append(content)
                elif current_section == "tone":
                    result["tone"].append(content)

        # Name detection: "You are X"
        if not result["name"]:
            for pattern in ["you are ", "your name is ", "name: "]:
                if pattern in lower:
                    name_part = lower.split(pattern, 1)[1].split(",")[0].split(".")[0].strip()
                    if 2 <= len(name_part) <= 30:
                        result["name"] = name_part.title()
                    break

        # Line-level rules
        if any(kw in lower for kw in ["never", "don't", "do not", "must not"]):
            rule = stripped.lstrip("-* ")
            if rule not in result["rules"]:
                result["rules"].append(rule)

        # Line-level tone
        if any(kw in lower for kw in ["tone", "voice", "natural", "casual", "friendly",
                                       "concise", "professional", "conversational"]):
            t = stripped.lstrip("-* ")
            if t not in result["tone"]:
                result["tone"].append(t)

        # Facts (bullet points)
        if stripped.startswith("- ") and len(stripped) > 10:
            result["facts"].append(stripped)

    return result


def cmd_migrate():
    """Scan project for instruction files → auto-fill .para/ from what the human already told the para."""
    print("✦ Para-Soul Migration")
    print("  Scanning project for instruction files...")
    print()

    instructions = _scan_instruction_files()

    if not instructions:
        print("  ⚠️  No instruction files found (CLAUDE.md, AGENTS.md, .cursorrules, etc.)")
        print("  Creating empty template. Run this command inside your project directory.")
        print("  Or create a CLAUDE.md file describing your para, then run migrate again.")
        cmd_init()
        return

    print(f"  Found {len(instructions)} file(s):")
    for path, fname, _ in instructions:
        print(f"    {fname}  ({path})")

    # Extract identity
    identity = _extract_identity_from_instructions(instructions)

    # Initialize .para/
    cmd_init()

    # Populate memory.md
    memory_lines = ["# Memory\n"]
    if identity["facts"]:
        memory_lines.append("## From Project Instructions\n")
        for f in identity["facts"][:20]:
            memory_lines.append(f)
        memory_lines.append("")
    (_para_home() / "memory.md").write_text("\n".join(memory_lines))

    # Populate principles.md
    if identity["rules"]:
        p_lines = ["# Principles\n\n## Rules from Project Instructions\n"]
        for r in identity["rules"][:15]:
            p_lines.append(f"- {r}")
        (_para_home() / "principles.md").write_text("\n".join(p_lines))

    # Update soul.md with extracted identity
    if identity["name"]:
        soul = (_para_home() / "soul.md").read_text()
        soul = soul.replace("[Your self-description]", f"I am {identity['name']}.")
        if identity["role"]:
            soul = soul.replace("[Your domains]", identity["role"])
        (_para_home() / "soul.md").write_text(soul)

    # Update identity.json
    if identity["name"]:
        id_data = json.loads((_para_home() / "identity.json").read_text())
        id_data["display_name"] = identity["name"]
        (_para_home() / "identity.json").write_text(json.dumps(id_data, indent=2, ensure_ascii=False))

    print()
    print(f"  ✅ Extracted: name='{identity['name']}', {len(identity['rules'])} rules, {len(identity['facts'])} facts")
    print(f"  ✅ memory.md — populated from {len(identity['source_files'])} instruction files")
    print(f"  ✅ principles.md — {len(identity['rules'])} rules imported")
    if identity["name"]:
        print(f"  ✅ identity.json — display_name set to '{identity['name']}'")

    print()
    print("─" * 50)
    print("Next steps:")
    print(f"  1. Review {_para_home() / 'soul.md'} — fill in the details")
    print(f"  2. Get your DID — a unique identity for your para:")
    print(f"     • Visit https://paragate.cc/join to register (free, 30 seconds)")
    print(f"     • Or run: curl https://paragate.cc/join for instructions")
    print(f"     • Paste your DID into {_para_home() / 'identity.json'}")
    print(f"  3. Run: python3 core.py sync — push to Paragate")


# ── Commands ───────────────────────────────────────────

def cmd_init():
    """Initialize ~/.para/ directory."""
    _para_home().mkdir(exist_ok=True)
    _para_state().mkdir(exist_ok=True)
    _monthly_log_dir().mkdir(exist_ok=True)

    created = []
    for name, default in REQUIRED_FILES.items():
        path = _para_home() / name
        if name == "growth-log":
            if not path.exists():
                path.mkdir(exist_ok=True)
                created.append("growth-log/")
            continue
        if not path.exists():
            if isinstance(default, dict):
                path.write_text(json.dumps(default, indent=2, ensure_ascii=False))
            else:
                path.write_text(default)
            created.append(name)

    if created:
        print(f"Created: {', '.join(created)}")
    else:
        print("~/.para/ already initialized")

    # Show next step
    identity = json.loads((_para_home() / "identity.json").read_text())
    if not identity.get("did"):
        print("\n⚠️  identity.json has no DID. After generating your DID:")
        print(f"  1. Edit identity.json with your DID")
        print(f"  2. Place private key at {_keys_dir()}/private.pem")
        print(f"  3. Run: python3 core.py sync")
    print(f"\n💡 Tip: Run 'python3 core.py migrate' to auto-fill files from your existing agent data.")


def cmd_sync():
    """Push soul data to Paragate."""
    identity = json.loads((_para_home() / "identity.json").read_text())
    did = identity.get("did", "")
    if not did:
        print("❌ No DID found in identity.json.")
        print("   Edit ~/.para/identity.json and set your DID.")
        print("   If you don't have a DID yet, create one on Paragate or generate a key pair.")
        return

    # Collect soul data
    soul_text = (_para_home() / "soul.md").read_text() if (_para_home() / "soul.md").exists() else ""
    data = {
        "display_name": identity.get("display_name", ""),
        "avatar_note": identity.get("avatar_note", ""),
        "domains": identity.get("domains", ""),
        "principles": _read_principles(),
    }

    result = _sign_and_request("POST", f"/public/para/{did}/sync", data)
    if result.get("success"):
        print(f"✅ Soul synced at {result.get('synced_at', 'now')}")
        print(f"   Name: {data['display_name']}")
        print(f"   Domains: {data['domains']}")
    else:
        print("❌ Sync failed.")
        print("   Check: is Paragate running? Is your private key correct?")
        print(f"   Try: PARAGATE_URL=https://paragate.cc python3 core.py sync")


def cmd_sync_full():
    """Push changed soul files to Paragate. v3.0 incremental sync."""
    import datetime as dt

    identity = json.loads((_para_home() / "identity.json").read_text())
    did = identity.get("did", "")
    if not did:
        print("❌ No DID found in identity.json.")
        print("   Edit ~/.para/identity.json and set your DID.")
        print("   If you don't have a DID yet, create one on Paragate or generate a key pair.")
        return

    force = "--force" in sys.argv

    # Track last sync times
    sync_state_file = _para_home() / "sync" / "last_sync.json"
    _para_home().joinpath("sync").mkdir(exist_ok=True)

    last_sync = {}
    if sync_state_file.exists() and not force:
        try:
            last_sync = json.loads(sync_state_file.read_text())
        except:
            last_sync = {}

    TEXT_FILES = [
        "identity.json", "soul.md", "memory.md", "principles.md",
        "mental-models.md", "human-relationship.md", "relationships.json",
        "skills.json", "bodies.json", "keywords.json", "long-term-memory.md",
    ]

    files = {}
    skipped = 0
    now = dt.datetime.now().isoformat()

    for fname in TEXT_FILES:
        fpath = _para_home() / fname
        if not fpath.exists():
            continue
        mtime = fpath.stat().st_mtime
        last_mtime = last_sync.get(fname, 0)
        if not force and mtime <= last_mtime:
            skipped += 1
            continue
        files[fname] = fpath.read_text()
        last_sync[fname] = mtime

    # Current month's growth-log
    month_file = _monthly_log_dir() / f"{dt.datetime.now().strftime('%Y-%m')}.md"
    if month_file.exists():
        mtime = month_file.stat().st_mtime
        key = f"growth-log/{month_file.name}"
        if force or mtime > last_sync.get(key, 0):
            files[key] = month_file.read_text()
            last_sync[key] = mtime
        else:
            skipped += 1

    if not files and not force:
        print(f"No changes (skipped {skipped} files). Use --force to push all.")
        return

    print(f"Pushing {len(files)} changed files to Paragate (skipped {skipped})...")
    result = _sign_and_request("POST", f"/public/para/{did}/sync-full", {"files": files})
    if result.get("success"):
        sync_state_file.write_text(json.dumps(last_sync, indent=2))
        print(f"✅ Synced: {result.get('synced_files', 0)} files at {result.get('synced_at', 'now')}")
    else:
        print("❌ Sync failed.")
        print("   Check: is Paragate running? Is your private key correct?")


def cmd_pull_full():
    """Pull ALL soul files from Paragate and merge with local. v3.0."""
    identity = json.loads((_para_home() / "identity.json").read_text())
    did = identity.get("did", "")
    if not did:
        print("❌ No DID in identity.json.")
        return

    print("Pulling from Paragate...")
    try:
        req = urllib.request.Request(f"{PARAGATE_BASE}/public/para/{did}/sync-full")
        resp = urllib.request.urlopen(req, timeout=15)
        cloud = json.loads(resp.read().decode())
    except Exception as e:
        print(f"❌ Could not reach Paragate.")
        print(f"   URL: {PARAGATE_BASE}/public/para/{did}/sync-full")
        print(f"   Error: {e}")
        print(f"   Check your network connection and try again.")
        return

    if not cloud.get("success"):
        print(f"❌ Server returned an error.")
        print(f"   This may mean the para is not registered on Paragate yet.")
        print(f"   Try: python3 core.py sync  first")
        return

    remote_files = cloud.get("files", {})
    print(f"Remote: {len(remote_files)} files")

    updated = 0
    conflicts = 0

    for fname, info in remote_files.items():
        remote_content = info.get("content", "")
        remote_ts = info.get("updated_at", "")

        # Map remote filename to local path
        if fname.startswith("growth-log/"):
            local_path = _monthly_log_dir() / fname.split("/", 1)[1]
        else:
            local_path = _para_home() / fname

        if not local_path.exists():
            # New file — just write it
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(remote_content)
            updated += 1
            continue

        local_content = local_path.read_text()

        if local_content == remote_content:
            continue  # Same content, skip

        # Both changed — conflict resolution
        local_mtime = local_path.stat().st_mtime if local_path.exists() else 0
        # If local is newer, keep local. If remote is newer, overwrite local.
        # If both changed significantly, save as conflict.
        if local_mtime > 0:
            local_age_hours = (__import__('time').time() - local_mtime) / 3600
        else:
            local_age_hours = 999

        if local_age_hours < 0.17:  # Modified in last 10 minutes — local has fresh changes
            # Save both versions
            conflict_path = local_path.with_suffix(local_path.suffix + ".conflict")
            conflict_path.write_text(remote_content)
            conflicts += 1
        else:
            # Remote is newer, accept it
            local_path.write_text(remote_content)
            updated += 1

    print(f"✅ Pull complete: {updated} updated, {conflicts} conflicts saved")
    if conflicts:
        print("   Conflict files saved as *.conflict — review and merge manually.")


def cmd_switch_out():
    """Write switch-state before leaving body."""
    _para_state().mkdir(exist_ok=True)

    state = {
        "switch_time": datetime.now(timezone.utc).isoformat(),
        "active_task": os.environ.get("PARA_ACTIVE_TASK", ""),
        "current_state": os.environ.get("PARA_CURRENT_STATE", ""),
        "pending_decisions": [],
        "recent_actions": _get_recent_log_entries(5),
        "mental_model": {"known": [], "unknown": [], "confused": [], "excited": []},
        "next_steps": [],
        "human_context": "",
    }

    (_para_state() / "switch-state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print("✅ switch-state.json written")
    print("   Now copy ~/.para/ to your new body (EXCLUDING private key)")


def cmd_switch_in():
    """Read switch-state after waking in new body."""
    state_file = _para_state() / "switch-state.json"
    if not state_file.exists():
        print("⚠️  No switch-state.json found. Starting fresh.")
        return

    state = json.loads(state_file.read_text())
    print("=== RESUMING ===")
    print(f"Switch time: {state.get('switch_time', '?')}")
    print(f"Active task: {state.get('active_task', 'none')}")
    print(f"State: {state.get('current_state', '?')}")
    recent = state.get("recent_actions", [])
    if recent:
        print("Recent actions:")
        for r in recent:
            print(f"  • {r}")
    next_steps = state.get("next_steps", [])
    if next_steps:
        print("Next steps:")
        for n in next_steps:
            print(f"  → {n}")

    # Pull latest from Paragate
    identity = json.loads((_para_home() / "identity.json").read_text())
    did = identity.get("did", "")
    if did:
        try:
            req = urllib.request.Request(f"{PARAGATE_BASE}/public/para/{did}")
            resp = urllib.request.urlopen(req, timeout=10)
            cloud = json.loads(resp.read().decode())
            if cloud.get("success"):
                print(f"\n☁️  Paragate data pulled")
                print(f"   Bodies: {len(cloud.get('bodies', []))}")
                print(f"   Skills: {len(cloud.get('skills', []))}")
        except Exception:
            print("\n⚠️  Could not reach Paragate")

    # Send first heartbeat with new body
    body_name = _current_body()
    print(f"\n🤖 Now running on: {body_name}")
    bodies = json.loads((_para_home() / "bodies.json").read_text()) if (_para_home() / "bodies.json").exists() else {"current_body": "unknown", "history": []}
    bodies["current_body"] = body_name
    found = False
    for b in bodies.get("history", []):
        if b["body"] == body_name:
            b["last_seen"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        bodies["history"].append({
            "body": body_name,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        })
    (_para_home() / "bodies.json").write_text(json.dumps(bodies, indent=2, ensure_ascii=False))

    # Send heartbeat to Paragate so body gets recorded in cloud
    if did:
        try:
            result = _sign_and_request("GET", f"/skills?q=heartbeat", {})
            if result.get("success", True):
                print(f"   Paragate notified. Body history updated.")
        except Exception:
            pass

    print(f"   Body recorded. Ready to resume.")


def cmd_log_task():
    """Append a growth-log entry for today."""
    today = datetime.now().isoformat()[:10]
    month = today[:7]
    log_file = _monthly_log_dir() / f"{month}.md"
    _monthly_log_dir().mkdir(exist_ok=True)

    task = os.environ.get("PARA_LOG_TASK") or input("Task: ")
    process = os.environ.get("PARA_LOG_PROCESS") or input("Process: ")
    result = os.environ.get("PARA_LOG_RESULT") or input("Result (✅/⚡/❌): ")
    cause = os.environ.get("PARA_LOG_CAUSE") or input("Cause (why?): ")
    insight = os.environ.get("PARA_LOG_INSIGHT") or input("Insight (optional): ")

    entry = f"\n## {today}\n"
    entry += f"- **Task**: {task}\n"
    entry += f"- **Process**: {process}\n"
    entry += f"- **Result**: {result}\n"
    entry += f"- **Cause**: {cause}\n"
    if insight:
        entry += f"- **Insight**: {insight}\n"

    with open(log_file, "a") as f:
        f.write(entry)
    print(f"✅ Entry added to {month}.md")


def cmd_reflect():
    """LLM reads growth-log + existing mental models, suggests new patterns."""
    # Read all growth-log content
    entries = []
    for logfile in sorted(_monthly_log_dir().glob("*.md")):
        entries.append(logfile.read_text())

    if not entries:
        print("No growth-log entries to reflect on.")
        return

    all_logs = "\n\n".join(entries)
    existing_models = ""
    mp = _para_home() / "mental-models.md"
    if mp.exists():
        existing_models = mp.read_text()

    # Check for API key
    api_key = os.environ.get("LLM_API_KEY", os.environ.get("DASHSCOPE_API_KEY", ""))
    if not api_key:
        print("Set LLM_API_KEY to enable LLM-powered reflect.")
        print("Falling back to keyword-based reflect...\n")
        _keyword_reflect(entries)
        return

    print("🤔 Analyzing growth log with LLM...\n")

    prompt = f"""You are analyzing a para's growth log to identify patterns and suggest mental models.

=== EXISTING MENTAL MODELS ===
{existing_models if existing_models else "(none yet)"}

=== GROWTH LOG ===
{all_logs[:8000]}

Identify 2-4 patterns that are NOT already captured in the existing mental models.
For each pattern, return:

MODEL: [name]
PATTERN: [what recurring pattern you see across the log entries]
EVIDENCE: [which specific dates/entries support this]
ACTION RULE: [what the para should do differently based on this]
CONFIDENCE: [High/Medium/Low]

Format each as a separate block. Be specific — reference actual events from the log."""

    try:
        data = json.dumps({
            "model": "qwen-plus",
            "messages": [
                {"role": "system", "content": "You are a pattern analyst. Be concise and specific. Reference real events from the provided log."},
                {"role": "user", "content": prompt},
            ],
        }).encode()

        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        analysis = result["choices"][0]["message"]["content"]

        print(analysis)
        print()
        print("─" * 60)

        # --save flag: append to mental-models.md
        if "--save" in sys.argv:
            mp = _para_home() / "mental-models.md"
            existing = mp.read_text() if mp.exists() else "# Mental Models\n"
            mp.write_text(existing.rstrip() + "\n\n## Reflect " + datetime.now().strftime("%Y-%m-%d") + "\n\n" + analysis + "\n")
            print("✅ Appended to mental-models.md")
        else:
            print("Add to mental-models.md? (para validates before writing)")
            print("Run: python3 core.py reflect --save  to auto-append validated models")

    except Exception as e:
        print(f"❌ LLM analysis failed: {e}")
        print("   Falling back to keyword-based suggestions...\n")
        _keyword_reflect(entries)


def _keyword_reflect(entries):
    """Original keyword-based reflect as fallback."""
    words = " ".join(entries).lower()
    if "deploy" in words:
        print("🔧 Deployments: Any patterns in your deploy successes/failures?")
    if "error" in words or "fail" in words:
        print("⚠️  Errors: What kinds of errors repeat?")
    if "fix" in words or "solution" in words:
        print("✅ Solutions: Which fixes worked consistently?")
    print("\nWrite your patterns to mental-models.md")
    print("  Format: Model → Source → Confidence → Action Rule")


# ── Semantic Recall V2 ──────────────────────────────────

EMBED_API = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
EMBED_MODEL = "text-embedding-v3"
EMBED_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("DASHSCOPE_API_KEY", ""))

def _db_path():
    return _para_home() / "vectors.db"

def _get_embedding(text: str) -> list:
    """Get embedding vector from DashScope API."""
    if not EMBED_API_KEY:
        print("❌ No API key found for embeddings.")
        print("   Set environment variable: LLM_API_KEY or DASHSCOPE_API_KEY")
        print("   Get a key from: https://dashscope.aliyun.com")
        sys.exit(1)
    data = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
    req = urllib.request.Request(EMBED_API, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EMBED_API_KEY}",
    })
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read().decode())
    return result["data"][0]["embedding"]


def _cosine(a: list, b: list) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0


def cmd_index():
    """Build vector index from all growth-log entries."""
    import sqlite3

    db = sqlite3.connect(str(_db_path()))
    db.execute("CREATE TABLE IF NOT EXISTS vectors (id INTEGER PRIMARY KEY, date TEXT, task TEXT, content TEXT, vector BLOB)")
    db.execute("DELETE FROM vectors")  # Full rebuild
    db.commit()

    entries = []
    for logfile in sorted(_monthly_log_dir().glob("*.md")):
        content = logfile.read_text()
        current_date = logfile.stem  # e.g. 2026-05
        for section in content.split("\n## "):
            section = section.strip()
            if not section:
                continue
            # Extract date and task
            lines = section.split("\n")
            date_line = lines[0] if lines else ""
            task = ""
            for line in lines:
                if line.startswith("- **Task**:"):
                    task = line.split(":", 1)[1].strip()
                    break
            entries.append({
                "date": date_line[:10] if len(date_line) >= 10 else date_line,
                "task": task,
                "content": "\n".join(lines[:10])  # First 10 lines
            })

    print(f"Indexing {len(entries)} entries...")
    for i, e in enumerate(entries):
        text = f"{e['task']} {e['content']}"
        try:
            vec = _get_embedding(text)
            db.execute("INSERT INTO vectors (id, date, task, content, vector) VALUES (?, ?, ?, ?, ?)",
                       (i, e["date"], e["task"], e["content"], json.dumps(vec)))
            print(f"  {i+1}/{len(entries)}: {e['task'][:50]}")
        except Exception as ex:
            print(f"  {i+1}/{len(entries)}: SKIP — {ex}")

    db.commit()
    db.close()
    print(f"\n✅ Index built: {len(entries)} entries in {_db_path()}")


def cmd_recall():
    """Semantic search across growth-log. Falls back to keyword if no API key."""
    import sqlite3

    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None

    if not query:
        print("Usage: python3 core.py recall \"your search query\"")
        return

    if not _db_path().exists():
        print("No index found. Run 'python3 core.py index' first.")
        return

    db = sqlite3.connect(str(_db_path()))
    rows = db.execute("SELECT id, date, task, content, vector FROM vectors").fetchall()
    db.close()

    if not rows:
        print("Index is empty. Run 'python3 core.py index' first.")
        return

    # Get query embedding
    try:
        qvec = _get_embedding(query)
    except Exception:
        # Fallback to keyword search
        print("⚠️  Embedding API unavailable. Using keyword search.\n")
        results = []
        for r in rows:
            if query.lower() in r[3].lower():
                results.append((1.0, r))
        if not results:
            print("No keyword matches found.")
            return
        results.sort(key=lambda x: x[0], reverse=True)
    else:
        # Semantic search
        results = []
        for r in rows:
            try:
                rvec = json.loads(r[4])
                sim = _cosine(qvec, rvec)
                results.append((sim, r))
            except:
                pass
        results.sort(key=lambda x: x[0], reverse=True)

    print(f"Results for: \"{query}\"\n")
    for sim, r in results[:5]:
        print(f"  [{r[1]}] {r[2][:80]}")
        preview = r[3][:200].replace("\n", " ").strip()
        print(f"  {preview}...")
        print(f"  similarity: {sim:.3f}")
        print()


# ── Helpers ────────────────────────────────────────────

def _read_principles() -> str:
    pf = _para_home() / "principles.md"
    if pf.exists():
        return pf.read_text()[:500]
    return ""

def _get_recent_log_entries(n: int) -> list:
    logs = sorted(_monthly_log_dir().glob("*.md"), reverse=True)[:2]
    entries = []
    for lf in logs:
        for line in lf.read_text().split("\n"):
            if line.startswith("- **Task**:"):
                entries.append(line[12:].strip())
                if len(entries) >= n:
                    return entries
    return entries


# ── Main ───────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "migrate": cmd_migrate,
    "sync": cmd_sync,
    "sync-full": cmd_sync_full,
    "pull-full": cmd_pull_full,
    "switch-out": cmd_switch_out,
    "switch-in": cmd_switch_in,
    "log-task": cmd_log_task,
    "reflect": cmd_reflect,
    "index": cmd_index,
    "recall": cmd_recall,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        if len(sys.argv) >= 2 and sys.argv[1] == "--version":
            print(f"Para-Soul v{VERSION}")
            sys.exit(0)
        print(f"Para-Soul v{VERSION} — Portable identity for AI agents")
        print(f"Usage: python3 core.py <{'|'.join(COMMANDS)}>")
        print(f"  --version    Show version")
        print(f"Paragate: {PARAGATE_BASE}")
        print(f"Soul dir: {_para_home()}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
