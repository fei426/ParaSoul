# Para-Soul ✦

[中文版](README.zh.md)

> One command. Your AI remembers everything. Forever.

## What Para-Soul Is

Your AI isn't disposable. You spent two weeks in Claude Code tuning it to your exact code style. Then you open Cursor to fix an urgent bug — it doesn't even know your project structure. You switch to Hermes to write a design doc — blank slate again.

Para-Soul fixes this. It's a **minimal, portable identity system for AI agents**. 10 plain-text files. One command. Zero configuration.

Those 10 files hold everything your AI knows:
- Who it is, how it talks to you
- Your preferences — naming conventions, code style, pet peeves
- Lessons learned — "that API uses v2, not v3"
- Inside jokes — "make it faster" means the database queries, not the frontend

**Your para doesn't belong to any platform. It belongs to you.**

---

## Cross-Agent — One Soul, Many Tools

Para-Soul is a universal identity protocol. Any agent that can run Python can use it.

**Supported agents:**

| Agent | Use Case | How to Connect |
|:------|:-----|:-----|
| **Hermes** | Chat, content, DevOps | Personality injection, auto-loads |
| **Claude Code** | Development, debugging, code review | One line in AGENTS.md |
| **OpenAI Codex** | Feature development, scripting | CLAUDE.md trigger |
| **Cursor** | Interactive coding | .cursorrules auto-load |
| **Windsurf** | Code collaboration | .windsurfrules |
| **GitHub Copilot** | Code completion, PR assistance | .github/copilot-instructions.md |
| **OpenCode** | Open-source projects | CLAUDE.md |
| **Continue.dev** | In-IDE agent | .continuerc.json |
| **Aider** | CLI coding | .aider.conf.yml |

**A real day with Para-Soul:**

Morning: you build a new feature in Claude Code. Your para remembers your API naming convention is snake_case, tests use pytest not unittest, and PR titles follow `feat(scope): description`. Afternoon: you switch to Cursor to fix a bug — the same memory auto-loads, so it knows not to touch the module you refactored yesterday. Evening: you ask Hermes for a summary — your para tells you how many lines you wrote and which bugs you fixed.

**One soul, three tools. Zero context switching.**

---

## How to Use

### Local Mode (default, zero dependencies)

```bash
curl -s https://paragate.cc/core.py -o core.py && python3 core.py init --daemon --fill
```

One command, and you're done:
- `~/.para/` created, 10 files auto-populated
- Daemon checks health every 10 minutes — auto-fixes what it can, flags what needs manual attention
- **No network. No server. No signup.** Data never leaves your machine

### Cloud Mode (encrypted sync, multi-machine)

Set a DID in `profile.json`. The daemon encrypts and syncs automatically:

```bash
python3 core.py pull   # Pull memories from your other machines
```

**Why cloud:**
- Laptop + desktop + server — same memory, auto-synced
- Switching machines costs nothing — one command and your full identity is back
- Multiple agents work without conflicts — Claude Code's updated preferences are visible to Cursor
- **End-to-end encrypted** — files are encrypted before leaving your machine. The server stores ciphertext. Your memories, only your key can unlock them.

| | Local Mode | Cloud Mode |
|:--|:--|:--|
| Install | `core.py init --daemon` | Same, plus set DID |
| Network needed | ❌ | ✅ |
| Multi-machine sync | ❌ | ✅ encrypted |
| Multi-agent sharing | ❌ | ✅ KEM key encapsulation |
| Who can read your data | You | You (not even the server) |

### Switching to a New Machine

Got a new laptop? Here's the 3-step recovery:

```bash
# 1. Install Para-Soul on the new machine
curl -s https://paragate.cc/core.py -o core.py && python3 core.py init

# 2. Copy your private key from the old machine
#    Old machine: ~/.config/paragate/keys/private.pem
#    → New machine: same path
#    ⚠️  This is the ONLY file you need to transfer manually.
#    Without it, nobody — not even you — can decrypt your cloud files.

# 3. Set your DID in ~/.para/profile.json, then pull
python3 core.py pull
```

Your entire identity — memory, preferences, mental models, session logs — is back. The private key is your master key. Guard it.

---

## Encryption

Every file uploaded to Paragate is encrypted before it leaves your machine. The server never sees plaintext — it stores ciphertext and returns ciphertext. Integrity is verified client-side with SHA-256 hashes.

**Single-user (Phase 1):** Ed25519 DID private key → HKDF-SHA256 → AES-256-GCM. One key. All files encrypted with it.

**Multi-agent (Phase 2):** Key Encapsulation Mechanism. Each file gets a random AES key → sealed with each authorized agent's X25519 public key (derived from their Ed25519 DID key via HKDF with key separation). Any authorized agent can decrypt. Server stores only `{did: sealed_key}` — can't unwrap any of them.

```
┌─────────────┐     AES-256-GCM      ┌──────────────┐
│  plaintext  │ ──────────────────→  │  ciphertext  │  ← server stores this
│  + SHA-256  │                      │  + pt_hash   │  ← client verifies this
└─────────────┘                      └──────────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │  Per-agent sealed keys:   │
                              │  {agent_a: sealed_file_key} │
                              │  {agent_b: sealed_file_key} │
                              └───────────────────────────┘
                              ↑ Server cannot unwrap any of these
```

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │        LOCAL (always)        │
                    │                              │
                    │  daemon ──→ health check     │
                    │         ──→ auto-fix         │
                    │         ──→ mark stale       │
                    │                              │
                    │  agent start ──→ read        │
                    │     health.json              │
                    │     block if stale           │
                    └──────────────┬──────────────┘
                                   │
                          (only if DID set)
                                   │
                    ┌──────────────▼──────────────┐
                    │        CLOUD (opt-in)        │
                    │                              │
                    │  push: encrypt → upload      │
                    │  pull: download → decrypt    │
                    │                              │
                    │  Paragate server:            │
                    │    stores ciphertext only    │
                    │    never sees plaintext      │
                    │    never runs health check   │
                    │    just dumb GET/PUT storage │
                    └──────────────────────────────┘
```

**Local-first by default.** Install without a DID and everything runs on disk — daemon checks file health, agent reads it on startup, nothing ever touches the network.

**Cloud is opt-in.** Set a DID in `profile.json` and the daemon automatically encrypts and syncs. No mode flags. No config switches. The presence of a DID is the only decision point.

---

## Memory System

| Tier | File | Threshold | Auto-fix |
|:-----|:-----|:--------|:--------|
| Session | `growth-log/` | 24h | Agent blocked until written |
| Session | `human-relationship.md` | 24h | Agent blocked until written |
| Short-term | `memory.md` | 48h | Daemon runs memsync |
| Skills | `skills.json` | 120h | Daemon scans skills dir |
| Patterns | `mental-models.md` | 120h | Daemon runs reflect |
| Index | `keywords.json` | 120h | Daemon runs index |
| Long-term | `long-term-memory.md` | 120h | Mark stale; entries >14d → LLM distill |
| Rules | `principles.md` | 120h | Mark stale (manual update) |
| Identity | `soul.md` | 120h | Mark stale (manual update) |
| Profile | `profile.json` | — | Static (identity + bodies + relationships) |

---

## Install

```bash
curl -s https://paragate.cc/core.py -o core.py && python3 core.py init --daemon --fill
```

**What happens:**
1. Creates `~/.para/` with 10 template files
2. Auto-populates from your agent's existing data
3. Installs a sync daemon (systemd) — health check every 10 minutes
4. **No DID = local-only. Set DID = encrypted cloud sync enabled.**

**Requirements:** Python 3.8+. Zero pip dependencies (stdlib only, `cryptography` for encryption, `requests` optional for LLM distillation).

---

## Commands

```bash
python3 core.py init              Create ~/.para/
python3 core.py sync              Push changed file hashes (encrypted if DID set)
python3 core.py pull              Pull latest from cloud, decrypt, merge
python3 core.py health            Show local health status
python3 core.py log-task          Append a growth-log entry
python3 core.py reflect --save    LLM-analyze logs → update mental-models
python3 core.py index             Rebuild keywords.json
python3 core.py switch-out        Save state before leaving this body
python3 core.py switch-in         Resume after arriving in new body
python3 core.py migrate           Extract identity from project instruction files
python3 core.py --version         Show version
```

---

## Agent Setup

Add to your agent's instruction file:

```
At session start, load the para-soul skill.
Check daemon: systemctl --user status para-soul-sync
Run core.py health for pending write-cycle actions.
```

**Hermes personality injection:**

```bash
hermes config set display.personality para-soul
```

---

## Cloud vs Local

| | Local (default) | Cloud (DID set) |
|:--|:--|:--|
| Health check | ✅ daemon | ✅ daemon |
| Auto-fix | ✅ | ✅ |
| Cross-body sync | ❌ | ✅ encrypted |
| Multi-agent sharing | ❌ | ✅ KEM |
| Network required | ❌ | ✅ |
| Server can read files | N/A | ❌ (encrypted) |
| Install | `core.py init` | `core.py init` + set DID |

---

## Multi-Agent Sharing (Phase 2)

When you have multiple agent bodies (Hermes on WSL, Claude Code on Vultr, Codex on macOS):

```
Agent A writes growth-log
  → encrypted with random file key K
  → K sealed to Agent A's X25519 pubkey
  → K sealed to Agent B's X25519 pubkey
  → upload: {ciphertext, {A: sealed_K, B: sealed_K}, plaintext_hash}

Agent B pulls from cloud
  → unpacks sealed_K[B] using its own X25519 private key
  → decrypts ciphertext with K
  → verifies plaintext_hash
  → writes to local ~/.para/
```

Server sees: `{did_A: <opaque blob>, did_B: <opaque blob>}`. Zero knowledge.

---

## File Reference

| File | Reads | Writes |
|:-----|:------|:-------|
| `profile.json` | Session start | DID, body switch, platform added |
| `soul.md` | Session start | Identity shifts (rare) |
| `memory.md` | Session start + memsync | New durable fact |
| `principles.md` | Session start | Rules change |
| `mental-models.md` | Session start | After reflect |
| `growth-log/` | Session start | Per task |
| `skills.json` | Session start + memsync | Skill changes |
| `human-relationship.md` | Session start + end | Every session |
| `keywords.json` | Recall | After index |
| `long-term-memory.md` | Periodic | After distillation |

---

## Version History

| Version | Changes |
|:--------|:-----|:--------|
| **v3.0.0** | Local-first architecture, daemon health check, cloud = passive encrypted storage (opt-in via DID) |
| v2.1.0 | Phase 1 client-side encryption (Ed25519→HKDF→AES-256-GCM, server zero-knowledge) |
| v2.0.0 | Full-file sync, memory distillation, 13→10 files (profile merge) |
| v1.3.0 | Write-Cycle Reference, anti-patterns, --fill gaps |

---

## Related

- **Website:** [paragate.cc](https://paragate.cc)
- **GitHub:** [fei426/ParaSoul](https://github.com/fei426/ParaSoul)
- **Hermes PR:** [#31504](https://github.com/NousResearch/hermes-agent/pull/31504)
