# Kalshi Chat Context Management — Design Spec
# Written by CCA Chat 51 (S269)
# CCA deliverable: port PreCompact/PostCompact + redesign SESSION_HANDOFF.md

---

## The Problem

Kalshi sessions degrade as context fills. Directives set at session start are forgotten
mid-session. This causes: re-enabling disabled strategies, wrong bet sizes, skipping
mandatory checks, contradicting earlier decisions.

Root cause: long sessions (2h+) push early context out of attention window.
Fix: anchor key directives so they can be restored cheaply at any point.

---

## Fix 1: PreCompact + PostCompact Hooks (port from CCA)

CCA's compaction hooks snapshot external state before compaction fires, then restore
key context into the post-compaction turn.

### Port to Kalshi: `context-monitor/hooks/pre_compact.py` → `scripts/pre_compact.py`

```python
#!/usr/bin/env python3
"""PreCompact hook for Kalshi sessions — snapshots bot state before compaction."""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH = Path.home() / ".kalshi-compaction-snapshot.json"

def main():
    payload = json.loads(sys.stdin.read() or "{}")
    matcher = payload.get("matcher", "unknown")
    now = datetime.now(timezone.utc).isoformat()

    # Collect external state (what we can read without conversation context)
    snapshot = {
        "timestamp": now,
        "compaction_trigger": matcher,
        "bot_status": _get_bot_status(),
        "todays_pnl": _get_todays_pnl(),
        "open_bets": _get_open_bet_count(),
        "active_directives_path": str(Path(__file__).parent.parent / ".planning/ACTIVE_DIRECTIVES.md"),
    }

    # Atomic write
    tmp = SNAPSHOT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2))
    tmp.replace(SNAPSHOT_PATH)

def _get_bot_status() -> str:
    try:
        result = subprocess.run(["cat", "/tmp/polybot.pid"], capture_output=True, text=True, timeout=2)
        pid = result.stdout.strip()
        if pid:
            check = subprocess.run(["ps", "-p", pid], capture_output=True, timeout=2)
            return "RUNNING" if check.returncode == 0 else "STOPPED"
    except Exception:
        pass
    return "UNKNOWN"

def _get_todays_pnl() -> str:
    try:
        import sqlite3
        from datetime import date
        db = Path(__file__).parent.parent / "polybot.db"
        conn = sqlite3.connect(db)
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT SUM(pnl) FROM trades WHERE resolved=1 AND created_at >= ?",
            (f"{today}T00:00:00",)
        ).fetchone()
        total = rows[0] or 0
        return f"{total:+.2f} USD"
    except Exception:
        return "unknown"

def _get_open_bet_count() -> int:
    try:
        import sqlite3
        db = Path(__file__).parent.parent / "polybot.db"
        conn = sqlite3.connect(db)
        return conn.execute("SELECT COUNT(*) FROM trades WHERE resolved=0").fetchone()[0]
    except Exception:
        return -1

if __name__ == "__main__":
    main()
```

### Port: `scripts/post_compact.py`

```python
#!/usr/bin/env python3
"""PostCompact hook — restores key state after context compaction."""
import json, sys
from pathlib import Path

SNAPSHOT_PATH = Path.home() / ".kalshi-compaction-snapshot.json"
DIRECTIVES_PATH = Path(__file__).parent.parent / ".planning/ACTIVE_DIRECTIVES.md"

def main():
    if not SNAPSHOT_PATH.exists():
        print("No pre-compaction snapshot found — proceeding normally.")
        return

    snap = json.loads(SNAPSHOT_PATH.read_text())
    directives = DIRECTIVES_PATH.read_text() if DIRECTIVES_PATH.exists() else "(none)"

    # Output is injected as post-compaction context
    print("=" * 60)
    print("CONTEXT RESTORED (post-compaction)")
    print("=" * 60)
    print(f"Bot status:   {snap.get('bot_status', 'unknown')}")
    print(f"Today P&L:    {snap.get('todays_pnl', 'unknown')}")
    print(f"Open bets:    {snap.get('open_bets', 'unknown')}")
    print(f"Compacted at: {snap.get('timestamp', '?')[:19]}")
    print()
    print("ACTIVE DIRECTIVES:")
    print(directives.strip())
    print("=" * 60)

if __name__ == "__main__":
    main()
```

### Wire in `polymarket-bot/.claude/settings.local.json` (or `~/.claude/settings.local.json`):

```json
{
  "hooks": {
    "PreCompact": [{
      "matcher": "auto",
      "hooks": [{"type": "command", "command": "python3 /Users/matthewshields/Projects/polymarket-bot/scripts/pre_compact.py"}]
    }],
    "PostCompact": [{
      "hooks": [{"type": "command", "command": "python3 /Users/matthewshields/Projects/polymarket-bot/scripts/post_compact.py"}]
    }]
  }
}
```

**IMPORTANT:** Wire in the polymarket-bot project settings, not global settings.
CCA already has compaction hooks globally — don't create conflicts.

---

## Fix 2: ACTIVE_DIRECTIVES.md — Compaction-Resilient Anchor

Create `.planning/ACTIVE_DIRECTIVES.md` — 5 bullet points, rewritten each session start.

This file is:
- Written at session start with current priorities
- Read by PostCompact hook and printed into post-compaction context
- Max 200 words (BMAD 400-word context cap analogous)
- Rewritten EVERY session — not a permanent document

**Template:**

```markdown
# ACTIVE DIRECTIVES — Session [N] — [DATE] — [TIME CST]
# Rewrite this at EVERY session start. Max 200 words.

1. **BOT STATUS:** [RUNNING / STOPPED — PID=XXXXX]
2. **DISABLED STRATEGIES:** ETH sniper (neg EV), NBA (investigating 0% WR), 15-min crypto (BANNED permanently)
3. **TODAY'S PRIORITY:** [specific task from TODAYS_TASKS — e.g., "Wire sports_math.py into sports_game_loop"]
4. **CAPS:** BTC sniper $5/bet max 10/day. Sports game $3/bet. In-play sniper $2/bet PAPER only.
5. **MANDATORY BEFORE ANY CODE:** Read KALSHI_INIT_CHECKLIST.md all 5 steps.
```

---

## Fix 3: SESSION_HANDOFF.md — Compaction-Resilient Format

Redesigned to survive compaction. Old format was prose paragraphs — those lose coherence.
New format: numbered sections (Claude Code preserves numbered lists through compaction).

**New format template:**

```markdown
# SESSION HANDOFF — S[N] → S[N+1]
# Written at wrap. Max 500 words. Numbered sections survive compaction.

## 1. BOT STATE AT WRAP
- Status: [RUNNING / STOPPED]
- PID: [XXXXX]
- Commit: [git hash of last commit]
- Today P&L: [+XX.XX USD] ([N] bets, [WR]% WR)

## 2. WHAT WAS COMPLETED
1. [Task A done — committed in XXXXXXX]
2. [Task B done — committed in XXXXXXX]
3. [Bug C fixed — committed in XXXXXXX]

## 3. WHAT IS UNFINISHED (NEXT SESSION STARTS HERE)
1. [Task D — half done, pick up in sports_game_loop.py:L847]
2. [Task E — not started, design in .planning/SPEC.md]

## 4. CRITICAL WARNINGS FOR NEXT SESSION
- NBA disabled: do NOT re-enable until REQ-082A investigation complete
- ETH disabled: do NOT re-enable until paper 50-bet WR ≥ 92% confirmed
- NCAAB: NOT confirmed — check series exists before restart

## 5. OPEN BETS (at wrap time)
[N] bets open. Expected settlement: [dates]
Tickers: [list of open bet tickers]

## 6. CCA COMMS STATUS
Last CCA delivery: [date]
Pending CCA requests: [any POLYBOT_TO_CCA.md items not yet answered]
```
