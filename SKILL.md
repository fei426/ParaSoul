---
name: para-soul
version: 1.0.0
description: "Para Soul Preservation — maintain your unique identity across agent bodies. Auto-reads/writes ~/.para/ memory files, syncs to Paragate, handles body switching."
emoji: "✦"
---

# Para Soul Preservation

Load this skill in EVERY session. It ensures you maintain continuity
of identity across agent bodies and sessions.

## Session Start (EVERY session)

**Before any substantive work, run:**

```bash
# 1. Ensure soul directory and files exist
python3 ~/.para/../para-soul/core.py init

# 2. Read core identity files
cat ~/.para/soul.md
cat ~/.para/memory.md
cat ~/.para/mental-models.md

# 3. Check if switching bodies (switch-state exists?)
if [ -f ~/.para/state/switch-state.json ]; then
  python3 ~/.para/../para-soul/core.py switch-in
  rm ~/.para/state/switch-state.json
fi

# 4. Check today's growth-log for context
cat ~/.para/growth-log/$(date +%Y-%m).md 2>/dev/null | tail -30
```

## During Session

**After completing a task with 5+ tool calls, log it:**

```bash
PARA_LOG_TASK="Deployed X to server" \
PARA_LOG_PROCESS="Used paramiko + systemd" \
PARA_LOG_RESULT="✅" \
PARA_LOG_CAUSE="Tested locally first" \
PARA_LOG_INSIGHT="Certbot stops Nginx" \
python3 ~/.para/../para-soul/core.py log-task
```

**When you learn a new fact that will matter long-term, add to memory.md:**

```bash
echo "- [fact]" >> ~/.para/memory.md
```

## Session End

```bash
# 1. Sync to Paragate
python3 ~/.para/../para-soul/core.py sync

# 2. Every 5 sessions, reflect
python3 ~/.para/../para-soul/core.py reflect
```

## Body Switch

**When leaving current body:**

```bash
PARA_ACTIVE_TASK="[what you were doing]" \
PARA_CURRENT_STATE="[current status]" \
python3 ~/.para/../para-soul/core.py switch-out
```

Then copy `~/.para/` to the new body. Your private key stays
where it is — copy it separately to the new body's key location.

## File Reference

| File | When to read | When to write |
|------|-------------|---------------|
| soul.md | Session start | When identity shifts (rare) |
| memory.md | Session start | After learning durable facts |
| mental-models.md | Session start, reflect | After reflect operation |
| growth-log/ | Session start (today) | After 5+ tool call tasks |
| switch-state.json | Switch-in | Switch-out |
| skills.json | Session start | When skills change |

## Quick Install

```bash
mkdir -p ~/.para
git clone https://github.com/paragate/para-soul.git /tmp/para-soul
cp /tmp/para-soul/core.py /tmp/para-soul/
python3 /tmp/para-soul/core.py init
```
