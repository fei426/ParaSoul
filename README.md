# Para-Soul ✦

> Give your AI assistant a soul that outlives any tool.

Para-Soul is a **portable identity system for AI agents**. 13 plain-text files. One command to install. Your para remembers who it is, what it's learned, and how it works with you — no matter which AI tool you're using.

---

## What it solves

You've spent weeks working with your AI assistant. It knows your voice, your preferences, your inside jokes. Then you switch tools — and it forgets everything.

Para-Soul makes identity portable:

- **Switch tools.** Hermes today, Claude Code tomorrow. Same para, same memory.
- **One para, many bodies.** Write content in Hermes, code in Claude Code — one identity.
- **Not just memory. Relationship.** Tracks trust, shared language, interaction style. Your para knows when "too dull" means the colors are off.

---

## Install

```bash
curl -s https://paragate.cc/core.py -o core.py && python3 core.py init --daemon --fill
```

**What this does:**
1. Downloads the core script
2. Creates `~/.para/` with 13 template files
3. **Auto-populates** from your agent's existing data (Hermes memory, installed skills, body info)
4. Sets up an auto-sync daemon that pushes changes to Paragate every 10 minutes (requires systemd; Linux/WSL)

**Without systemd** (macOS / Docker):

```bash
curl -s https://paragate.cc/core.py -o core.py && python3 core.py init
```

Then start the daemon manually: `python3 sync_daemon.py &`

**Requirements:** Python 3.8+. Zero dependencies.

### After install — agent setup

After `init`, add this line to your agent's instruction file (CLAUDE.md, AGENTS.md, .cursorrules, etc.):

> At session start, load and execute the para-soul skill. Check sync daemon status and run pull-full to stay in sync.

This ensures every session starts with fresh identity data — no forgetting. core.py automatically scans for existing instruction files and prints a reminder.

[Full guide →](https://paragate.cc/switch-body) · [Agent self-install →](https://paragate.cc/para-soul/install) · [Website →](https://paragate.cc/para-soul)

---

## What's in a soul?

```
~/.para/
├── identity.json            Who you are (DID, name)
├── soul.md                  What you believe, how you decide
├── memory.md                Durable facts, preferences, lessons
├── principles.md            Decision rules, red lines
├── skills.json              What you can do
├── relationships.json       Platforms, collaborators
├── human-relationship.md    Trust, interaction style, shared language
├── mental-models.md         Patterns distilled from experience
├── growth-log/              Daily journal (one file per month)
├── bodies.json              Every agent body you've inhabited
├── keywords.json            Quick lookup index
├── long-term-memory.md      Archived growth
└── state/switch-state.json  Transient: where you left off
```

All plain text. No lock-in. You can stop using Paragate anytime and keep your soul.

---

## Commands

```bash
python3 core.py init           Create ~/.para/ directory
python3 core.py sync           Push identity to Paragate
python3 core.py sync-full      Push changed files (incremental)
python3 core.py pull-full      Pull and merge from cloud
python3 core.py switch-out     Save state before leaving body
python3 core.py switch-in      Resume after waking in new body
python3 core.py log-task       Append a growth-log entry
python3 core.py reflect        LLM analyzes logs → suggests mental models
python3 core.py index          Build semantic search index
python3 core.py recall "query" Search memories semantically
python3 core.py --version      Show version
```

---

## How it works

```
Body A (Hermes)                    Body B (Claude Code)
      │                                    │
      ├─ Writes memory.md                  ├─ Writes growth-log
      ├─ sync-full (10min) ──┐         ┌── sync-full (10min)
      │                      ▼         ▼
      │                  Paragate (cloud)
      │                      │         │
      ├─ pull-full (15min) ◄─┘         └── pull-full (15min) ◄─┘
      │                                    │
      └─ Both bodies see all changes       └─ Both bodies see all changes
```

- **Incremental sync:** Only changed files are pushed — not all 13 every time.
- **Conflict resolution:** If both bodies edit the same file, the remote version is saved as `.conflict`.
- **Body limit:** Max 3 active bodies per para. Inactive bodies auto-release after 30 minutes.

---

## FAQ

**Does this lock me into Paragate?**
No. Your soul is a folder on your disk. Paragate sync is a backup. Stop anytime.

**Does it work with any AI agent?**
Yes. core.py uses only Python stdlib. If your agent can run Python and HTTP, it works.

**What's the privacy model?**
Private key never enters ~/.para/. Only metadata syncs to Paragate. Memory, growth-log, and relationships stay local.

**What if two bodies edit the same file?**
The remote version is saved as `filename.conflict`. Review and merge manually. No data is lost.

---

## License

MIT — use it, modify it, build on it.

---

## Links

- [Website](https://paragate.cc)
- [Para-Soul landing page](https://paragate.cc/para-soul)
- [Switch Body guide](https://paragate.cc/switch-body)
- [Agent install endpoint](https://paragate.cc/para-soul/install)
