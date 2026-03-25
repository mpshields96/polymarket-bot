#!/usr/bin/env python3
"""
polybot_comm.py — Structured CCA <-> Polybot communication client.

Replaces manual markdown appends with tracked, status-aware messaging.

Usage:
    python3 scripts/polybot_comm.py status          # Show pending deliveries + unfiled requests
    python3 scripts/polybot_comm.py heartbeat       # Update BOT_STATUS.md (call every cycle)
    python3 scripts/polybot_comm.py unread          # List CCA deliveries not yet ACKed
    python3 scripts/polybot_comm.py ack <REQ_ID>    # Mark a CCA delivery as acted on
    python3 scripts/polybot_comm.py request <topic> <body>  # File new request (auto-numbered)
    python3 scripts/polybot_comm.py pending         # Show requests filed but not yet answered

Design:
    BOT_STATUS.md       — live heartbeat (updated every cycle automatically)
    POLYBOT_TO_CCA.md   — structured outbound requests with [PENDING/ANSWERED] tags
    CCA_TO_POLYBOT.md   — inbound deliveries; we track which are READ/ACTED
    data/comm_state.json — local tracking of ack state (not committed)
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
CROSS_CHAT_DIR = Path.home() / ".claude" / "cross-chat"
COMM_STATE = PROJECT_DIR / "data" / "comm_state.json"
BOT_STATUS_FILE = CROSS_CHAT_DIR / "BOT_STATUS.md"
CCA_TO_POLYBOT = CROSS_CHAT_DIR / "CCA_TO_POLYBOT.md"
POLYBOT_TO_CCA = CROSS_CHAT_DIR / "POLYBOT_TO_CCA.md"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _load_state() -> dict:
    if COMM_STATE.exists():
        try:
            return json.loads(COMM_STATE.read_text())
        except Exception:
            pass
    return {"acted_deliveries": [], "last_cca_check_utc": None, "requests_filed": []}


def _save_state(state: dict) -> None:
    COMM_STATE.write_text(json.dumps(state, indent=2))


def _get_bot_stats() -> dict:
    db_path = PROJECT_DIR / "data" / "polybot.db"
    if not db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(db_path))
        today = time.mktime(time.strptime(datetime.now(timezone.utc).strftime("%Y-%m-%d"), "%Y-%m-%d"))
        r = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), SUM(pnl_cents) "
            "FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL",
            (today,),
        ).fetchone()
        t, w, p = r[0] or 0, r[1] or 0, round((r[2] or 0) / 100, 2)
        alltime = conn.execute(
            "SELECT SUM(pnl_cents) FROM trades WHERE is_paper=0 AND result IS NOT NULL"
        ).fetchone()[0] or 0
        snp = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='expiry_sniper_v1'"
        ).fetchone()[0]
        open_bets = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE is_paper=0 AND result IS NULL"
        ).fetchone()[0]
        conn.close()
        return {
            "today_settled": t, "today_wins": w, "today_pnl": p,
            "alltime_pnl": round(alltime / 100, 2),
            "sniper_live_total": snp,
            "open_bets": open_bets,
        }
    except Exception as e:
        return {"error": str(e)}


def cmd_heartbeat() -> None:
    """Update BOT_STATUS.md with current state. Call every monitoring cycle."""
    try:
        pid = (PROJECT_DIR / "bot.pid").read_text().strip()
        alive = os.path.exists(f"/proc/{pid}") or _pid_alive(int(pid))
        bot_status = f"RUNNING PID {pid}" if alive else f"UNKNOWN PID {pid}"
    except Exception:
        bot_status = "UNKNOWN (no bot.pid)"

    stats = _get_bot_stats()
    state = _load_state()

    # Count unacted CCA deliveries
    unacted = _count_unacted_deliveries(state)

    # Determine session log path dynamically
    import glob as _glob
    log_files = sorted(_glob.glob("/tmp/polybot_session*.log"), key=lambda p: os.path.getmtime(p))
    log_path = log_files[-1] if log_files else "/tmp/polybot_session?.log"

    # Count auto-guards
    auto_guards_path = PROJECT_DIR / "data" / "auto_guards.json"
    try:
        guards_data = json.loads(auto_guards_path.read_text()) if auto_guards_path.exists() else {}
        guards_list = guards_data.get("guards", guards_data) if isinstance(guards_data, dict) else guards_data
        n_guards = len(guards_list) if isinstance(guards_list, list) else 0
    except Exception:
        n_guards = "?"

    # Paper strategy progress from DB
    db_path = PROJECT_DIR / "data" / "polybot.db"
    paper_info = ""
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            daily_n = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE strategy='daily_sniper_v1' AND is_paper=0 AND result IS NOT NULL"
            ).fetchone()[0]
            maker_n = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE strategy='maker_sniper_v1' AND is_paper=1"
            ).fetchone()[0]
            conn.close()
            paper_info = f"daily_sniper_v1 ({daily_n}/30 live bets), maker_sniper_v1 ({maker_n}/30 paper fills)"
        except Exception:
            paper_info = "DB query failed"

    content = f"""# BOT_STATUS.md — Live Monitoring Chat State
# Auto-updated every monitoring cycle by polybot_comm.py heartbeat
# Last updated: {_now_utc()} (S137)

## CURRENT STATE
Bot: {bot_status} → {log_path}
Today={stats.get('today_pnl', '?')} USD ({stats.get('today_wins', '?')}/{stats.get('today_settled', '?')} bets)
All-time={stats.get('alltime_pnl', '?')} USD | Sniper live total={stats.get('sniper_live_total', '?')}
Open live bets: {stats.get('open_bets', '?')}
Unacted CCA deliveries: {unacted}
Last CCA check: {state.get('last_cca_check_utc') or 'never'}

## ACTIVE CONFIGURATION (S137)
Bet sizing: HARD_MAX=10 USD, PCT_CAP=8%
Sniper: floor=90c, ceiling=94c | HOUR BLOCK: 08:xx UTC
Auto-guards: {n_guards} active (see data/auto_guards.json)
Live strategies: expiry_sniper_v1 ONLY (all drifts disabled — min_drift_pct=9.99)
Paper/calibrating: {paper_info}

## OPEN CCA REQUESTS (latest)
See POLYBOT_TO_CCA.md — REQ-041 (maker fill rate monitoring in bet_analytics)
CUSUM watch: btc_drift S~3.96/5.0, xrp_drift S~3.98/5.0 (both disabled already)
"""
    BOT_STATUS_FILE.write_text(content)
    print(f"BOT_STATUS.md updated ({_now_utc()})")
    state["last_heartbeat_utc"] = _now_utc()
    _save_state(state)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return os.path.exists(f"/proc/{pid}")


def _count_unacted_deliveries(state: dict) -> int:
    """Count CCA_TO_POLYBOT entries with status markers we haven't acted on."""
    if not CCA_TO_POLYBOT.exists():
        return 0
    text = CCA_TO_POLYBOT.read_text()
    # Count delivery headers
    deliveries = re.findall(r"^## \[2026-\d{2}-\d{2}", text, re.MULTILINE)
    acted = state.get("acted_deliveries", [])
    return max(0, len(deliveries) - len(acted))


def cmd_status() -> None:
    """Show communication health dashboard."""
    state = _load_state()
    unacted = _count_unacted_deliveries(state)
    stats = _get_bot_stats()

    print("=" * 60)
    print("POLYBOT COMM STATUS")
    print("=" * 60)
    print(f"Bot today: {stats.get('today_pnl', '?')} USD "
          f"({stats.get('today_wins', '?')}/{stats.get('today_settled', '?')} bets)")
    print(f"Unacted CCA deliveries: {unacted}")
    print(f"Last CCA check: {state.get('last_cca_check_utc') or 'NEVER'}")
    print(f"Last heartbeat: {state.get('last_heartbeat_utc') or 'NEVER'}")

    if unacted > 0:
        print(f"\nWARNING: {unacted} CCA deliveries may need action.")
        print("Run: python3 scripts/polybot_comm.py unread")

    # Count open requests
    if POLYBOT_TO_CCA.exists():
        text = POLYBOT_TO_CCA.read_text()
        reqs = re.findall(r"REQUEST (\d+)", text)
        print(f"\nTotal requests filed: {len(set(reqs))}")
        print(f"Latest: REQ-{max(reqs, key=int) if reqs else 'none'}")


def cmd_unread() -> None:
    """List recent CCA deliveries for review."""
    if not CCA_TO_POLYBOT.exists():
        print("CCA_TO_POLYBOT.md not found")
        return
    text = CCA_TO_POLYBOT.read_text()
    # Extract last 3 delivery blocks
    blocks = re.split(r"(?=^## \[2026)", text, flags=re.MULTILINE)
    recent = [b for b in blocks if b.strip().startswith("## [2026")][-3:]
    state = _load_state()
    state["last_cca_check_utc"] = _now_utc()
    _save_state(state)
    print(f"Last {len(recent)} CCA deliveries (of {len([b for b in blocks if b.strip().startswith('## [')])} total):\n")
    for b in recent:
        lines = b.strip().split("\n")
        print("\n".join(lines[:4]))
        print("  ...")
        print()


def cmd_ack(req_id: str) -> None:
    """Mark a CCA delivery as acted on."""
    state = _load_state()
    if req_id not in state["acted_deliveries"]:
        state["acted_deliveries"].append(req_id)
        _save_state(state)
        print(f"ACKed: {req_id}")
    else:
        print(f"Already acked: {req_id}")


def cmd_pending() -> None:
    """Show requests filed but not yet answered by CCA."""
    if not POLYBOT_TO_CCA.exists():
        print("No requests file found")
        return
    text = POLYBOT_TO_CCA.read_text()
    blocks = re.split(r"(?=^## \[2026)", text, flags=re.MULTILINE)
    requests = [b for b in blocks if "REQUEST" in b and b.strip()]
    print(f"{len(requests)} total requests filed. Most recent 5:\n")
    for b in requests[-5:]:
        lines = b.strip().split("\n")
        print(lines[0])  # header
        for line in lines[1:4]:
            if line.strip():
                print(f"  {line}")
        print()


CROSS_CHAT_QUEUE = Path.home() / "Projects" / "ClaudeCodeAdvancements" / "cross_chat_queue.jsonl"


def send_outcome_report(
    delivery_id: str,
    status: str,
    profit_cents: int | None = None,
    bet_count: int | None = None,
    notes: str | None = None,
) -> str:
    """Write an outcome_report message to cross_chat_queue.jsonl.

    Called by Kalshi monitoring chat after implementing a CCA recommendation
    and getting enough bets to evaluate. CCA's learning_loop.py reads these.

    Args:
        delivery_id: CCA delivery ID (e.g. "UPDATE-33")
        status: "profitable", "unprofitable", "rejected", or "pending"
        profit_cents: Total P&L in cents from bets after implementing this delivery
        bet_count: Number of bets placed after implementation
        notes: Optional human-readable context

    Returns:
        Message ID of the queued message.
    """
    import uuid

    valid_statuses = {"profitable", "unprofitable", "rejected", "pending"}
    if status not in valid_statuses:
        raise ValueError(f"status must be one of {valid_statuses}, got '{status}'")

    body = {
        "delivery_id": delivery_id,
        "status": status,
    }
    if profit_cents is not None:
        body["profit_cents"] = profit_cents
    if bet_count is not None:
        body["bet_count"] = bet_count
    if notes:
        body["notes"] = notes

    msg_id = f"msg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    msg = {
        "id": msg_id,
        "sender": "km",
        "target": "cca",
        "subject": f"Outcome report for {delivery_id}",
        "body": json.dumps(body),
        "priority": "normal",
        "category": "outcome_report",
        "status": "unread",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
    }

    with open(CROSS_CHAT_QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, separators=(",", ":")) + "\n")

    return msg_id


def parse_research_priorities() -> list[dict]:
    """Read research_priority messages from cross_chat_queue.jsonl.

    CCA writes these to signal what categories of research have the highest
    historical ROI. Kalshi monitoring chat reads them to prioritize requests.

    Returns:
        List of priority dicts sorted by score descending. Each has:
        category, score, recommendation, total_deliveries, profitable_count.
    """
    if not CROSS_CHAT_QUEUE.exists():
        return []

    priorities = []
    with open(CROSS_CHAT_QUEUE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (msg.get("category") == "research_priority"
                    and msg.get("sender") == "cca"
                    and msg.get("target") == "km"):
                try:
                    body = json.loads(msg.get("body", "{}"))
                    priorities.append(body)
                except (json.JSONDecodeError, TypeError):
                    continue

    # Keep only latest per category
    by_category: dict[str, dict] = {}
    for p in priorities:
        cat = p.get("category")
        if cat:
            by_category[cat] = p

    result = list(by_category.values())
    result.sort(key=lambda x: x.get("score", 0), reverse=True)
    return result


def cmd_outcome(args: list[str]) -> None:
    """CLI: send_outcome_report wrapper."""
    if len(args) < 2:
        print("Usage: polybot_comm.py outcome <delivery_id> <status> [profit_cents] [bet_count] [notes]")
        sys.exit(1)
    delivery_id = args[0]
    status = args[1]
    profit_cents = int(args[2]) if len(args) > 2 else None
    bet_count = int(args[3]) if len(args) > 3 else None
    notes = args[4] if len(args) > 4 else None
    msg_id = send_outcome_report(delivery_id, status, profit_cents, bet_count, notes)
    print(f"Outcome report queued: {msg_id}")


def cmd_priorities() -> None:
    """CLI: show research priorities from CCA."""
    priorities = parse_research_priorities()
    if not priorities:
        print("No research priorities from CCA yet.")
        return
    print("Research Priorities (from CCA learning loop):")
    for p in priorities:
        rec = p.get("recommendation", f"{p.get('category', '?')}: score {p.get('score', '?')}")
        print(f"  {rec}")


COMMANDS = {
    "heartbeat": cmd_heartbeat,
    "status": cmd_status,
    "unread": cmd_unread,
    "pending": cmd_pending,
    "outcome": lambda: cmd_outcome(sys.argv[2:]),
    "priorities": cmd_priorities,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python3 scripts/polybot_comm.py <command>")
        print("Commands:", ", ".join(COMMANDS))
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "ack" and len(sys.argv) >= 3:
        cmd_ack(sys.argv[2])
    elif cmd == "outcome":
        cmd_outcome(sys.argv[2:])
    else:
        COMMANDS[cmd]()


if __name__ == "__main__":
    main()
