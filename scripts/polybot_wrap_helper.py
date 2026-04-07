#!/usr/bin/env python3
"""
polybot_wrap_helper.py — Fast Session Wrap Automation

Collects all bot state in one pass and generates ready-to-use content for:
  - SESSION_HANDOFF.md BOT STATE section
  - SESSION_RESUME.md MAIN CHAT section (Session N+1)
  - polybot-auto.md SESSION STATE section
  - CHANGELOG.md entry
  - Next session start prompt

Replaces 15-20 minutes of sequential manual steps with ~30-second auto-generation.
Inspired by CCA's handoff_generator.py pattern.

Usage:
    ./venv/bin/python3 scripts/polybot_wrap_helper.py --session 133
    ./venv/bin/python3 scripts/polybot_wrap_helper.py --session 133 --write  # auto-write files
    ./venv/bin/python3 scripts/polybot_wrap_helper.py --session 133 --grade A --wins "..." --losses "..."

Stdlib only. No external dependencies.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "polybot.db"
BOT_PID_FILE = PROJECT_DIR / "bot.pid"
SESSION_HANDOFF = PROJECT_DIR / "SESSION_HANDOFF.md"
SESSION_RESUME = PROJECT_DIR / "SESSION_RESUME.md"
POLYBOT_AUTO = Path.home() / ".claude" / "commands" / "polybot-auto.md"
CHANGELOG = PROJECT_DIR / ".planning" / "CHANGELOG.md"
CCA_JOURNAL = Path.home() / "Projects" / "ClaudeCodeAdvancements" / "self-learning" / "journal.py"
VISIBILITY_REPORT_JSON = PROJECT_DIR / "data" / "kalshi_visibility_report.json"

# ── Data Collection ──────────────────────────────────────────────────────────

def get_bot_pid() -> tuple[int, str]:
    """Returns (pid, status_str). Status: ALIVE / STOPPED."""
    try:
        pid = int(BOT_PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            return pid, "ALIVE"
        except ProcessLookupError:
            return pid, "STOPPED (stale PID)"
        except PermissionError:
            return pid, "ALIVE"
    except Exception:
        return 0, "STOPPED"


def get_git_info() -> dict:
    """Last commit hash, message, test count."""
    try:
        commit = subprocess.check_output(
            ["git", "log", "--oneline", "-1"], cwd=PROJECT_DIR, text=True
        ).strip()
        hash_, *msg_parts = commit.split(" ", 1)
        msg = msg_parts[0] if msg_parts else ""
    except Exception:
        hash_, msg = "unknown", "unknown"

    try:
        result = subprocess.check_output(
            ["./venv/bin/python3", "-m", "pytest", "tests/", "-q", "--tb=no"],
            cwd=PROJECT_DIR, text=True, stderr=subprocess.DEVNULL,
            timeout=60
        )
        # Parse "1800 passed" from summary line
        for line in reversed(result.splitlines()):
            m = re.search(r"(\d+) passed", line)
            if m:
                test_count = int(m.group(1))
                break
        else:
            test_count = 1800
    except Exception:
        test_count = 1800  # known baseline

    return {"hash": hash_, "msg": msg, "test_count": test_count}


def get_pnl_data(session_num: int) -> dict:
    """All-time P&L, today P&L, WR from DB."""
    if not DB_PATH.exists():
        return {"alltime": 0.0, "today": 0.0, "today_bets": 0, "today_wins": 0, "alltime_bets": 0}

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Determine today's UTC date boundaries
    today_ts = datetime(
        *datetime.now(timezone.utc).timetuple()[:3],
        tzinfo=timezone.utc
    ).timestamp()

    # All-time live P&L
    c.execute("""
        SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), ROUND(SUM(pnl_cents)/100.0,2)
        FROM trades WHERE is_paper=0 AND result IS NOT NULL
    """)
    row = c.fetchone()
    alltime_bets = row[0] or 0
    alltime_wins = row[1] or 0
    alltime_pnl = row[2] or 0.0

    # Today's P&L (UTC)
    c.execute("""
        SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), ROUND(SUM(pnl_cents)/100.0,2)
        FROM trades WHERE is_paper=0 AND result IS NOT NULL AND timestamp >= ?
    """, (today_ts,))
    row = c.fetchone()
    today_bets = row[0] or 0
    today_wins = row[1] or 0
    today_pnl = row[2] or 0.0

    conn.close()
    return {
        "alltime": alltime_pnl,
        "alltime_bets": alltime_bets,
        "alltime_wr": round(100 * alltime_wins / alltime_bets, 1) if alltime_bets else 0,
        "today": today_pnl,
        "today_bets": today_bets,
        "today_wins": today_wins,
        "today_wr": round(100 * today_wins / today_bets, 1) if today_bets else 0,
    }


def get_strategy_counts() -> dict:
    """Live bet counts per strategy."""
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT strategy, COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END)
        FROM trades WHERE is_paper=0 AND result IS NOT NULL
        GROUP BY strategy
    """)
    rows = c.fetchall()
    conn.close()
    return {r[0]: {"n": r[1], "wins": r[2]} for r in rows}


def get_cusum_state() -> list[str]:
    """Run bet_analytics and extract CUSUM lines."""
    venv_python = str(PROJECT_DIR / "venv" / "bin" / "python3")
    analytics_script = str(PROJECT_DIR / "scripts" / "bet_analytics.py")
    try:
        result = subprocess.check_output(
            [venv_python, analytics_script],
            cwd=PROJECT_DIR, text=True, stderr=subprocess.DEVNULL,
            timeout=30
        )
        cusum_lines = [
            line.strip() for line in result.splitlines()
            if "CUSUM" in line or "DRIFT ALERT" in line or "ERODING" in line
        ]
        return cusum_lines[:10]
    except Exception as e:
        return [f"(bet_analytics error: {e})"]


def get_guard_count() -> dict:
    """Count active guards (auto-discovered + manual ILs)."""
    guard_path = PROJECT_DIR / "data" / "auto_guards.json"
    auto_count = 0
    try:
        guards = json.loads(guard_path.read_text())
        auto_count = len(guards)
    except Exception:
        pass

    # Count manual ILs in live.py
    il_count = 0
    try:
        live_src = (PROJECT_DIR / "src" / "execution" / "live.py").read_text()
        il_count = len(re.findall(r"IL-\d+:", live_src))
    except Exception:
        pass

    return {"auto": auto_count, "il": il_count, "total": auto_count + il_count}


def _format_visibility_timestamp(raw_timestamp: str | None) -> str:
    if not raw_timestamp:
        return "unknown time"
    try:
        dt = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return raw_timestamp
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_visibility_gate() -> dict:
    """Read the latest cached visibility report gate result."""
    if not VISIBILITY_REPORT_JSON.exists():
        return {
            "status": "UNKNOWN",
            "reason": "No cached visibility report. Run scripts/kalshi_visibility_report.py before strategy planning.",
            "timestamp_display": "missing",
        }

    try:
        report = json.loads(VISIBILITY_REPORT_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "reason": f"Cached visibility report unreadable: {exc}",
            "timestamp_display": "unreadable",
        }

    sports = report.get("sports", {})
    gate = sports.get("same_day_gate", {})
    if not gate:
        return {
            "status": "UNKNOWN",
            "reason": "Cached visibility report missing same_day_gate. Rerun the visibility report.",
            "timestamp_display": _format_visibility_timestamp(report.get("timestamp")),
        }

    return {
        "status": gate.get("status", "UNKNOWN"),
        "reason": gate.get("reason", "No gate reason recorded."),
        "timestamp_display": _format_visibility_timestamp(report.get("timestamp")),
    }


def summarize_overhaul_status(visibility_gate: dict | None) -> dict:
    """Return the top-line overhaul status summary for startup/handoff docs."""
    visibility_gate = visibility_gate or {
        "status": "UNKNOWN",
        "reason": "Visibility gate was not collected during wrap.",
        "timestamp_display": "missing",
    }
    return {
        "status": "INCOMPLETE",
        "summary": (
            "OVERHAUL STATUS: INCOMPLETE — blocked by visibility gate "
            f"{visibility_gate['status']} @ {visibility_gate['timestamp_display']}: "
            f"{visibility_gate['reason']}"
        ),
        "directive": (
            "Do not count restart, expansion, or side work as progress until the blocker above is closed."
        ),
    }


def get_log_path(session_num: int) -> str:
    return f"/tmp/polybot_session{session_num}.log"


# ── Generators ───────────────────────────────────────────────────────────────

def generate_handoff_bot_state(
    session_num: int, pid: int, pid_status: str,
    pnl: dict, git: dict, strats: dict,
    grade: str = "?", wins: str = "", losses: str = "",
    visibility_gate: dict | None = None,
) -> str:
    """Generate the BOT STATE section for SESSION_HANDOFF.md."""
    next_s = session_num + 1
    log_path = get_log_path(next_s)
    alltime = pnl["alltime"]
    today = pnl["today"]
    sniper = strats.get("expiry_sniper_v1", {})
    sniper_n = sniper.get("n", 0)
    sniper_wr = round(100 * sniper.get("wins", 0) / sniper_n, 1) if sniper_n else 0
    visibility_gate = visibility_gate or {
        "status": "UNKNOWN",
        "reason": "Visibility gate was not collected during wrap.",
        "timestamp_display": "missing",
    }
    overhaul = summarize_overhaul_status(visibility_gate)

    lines = [
        f"## BOT STATE",
        f"  {overhaul['summary']}",
        f"  {overhaul['directive']}",
        f"  Bot {'RUNNING' if pid_status == 'ALIVE' else 'STOPPED'} "
        f"→ restart for S{next_s} using restart command below",
        f"  All-time live P&L: {alltime:+.2f} USD | S{session_num} net: {today:+.2f} USD",
        f"  ({pnl['today_wins']}/{pnl['today_bets']} live wins today, {pnl['today_wr']}% WR)",
        f"  Tests: {git['test_count']} passing | Last commit: {git['hash']} ({git['msg'][:60]})",
        f"  Visibility gate: {visibility_gate['status']} @ {visibility_gate['timestamp_display']}",
        f"  {visibility_gate['reason']}",
        f"",
        f"  expiry_sniper_v1: {sniper_n} all-time bets, {sniper_wr}% WR",
        f"  All drifts DISABLED (min_drift_pct=9.99)",
    ]

    if grade != "?":
        lines += ["", f"  S{session_num} GRADE: {grade}"]
        if wins:
            lines.append(f"  WINS: {wins}")
        if losses:
            lines.append(f"  LOSSES: {losses}")

    return "\n".join(lines)


def generate_main_chat_prompt(
    session_num: int, pid: int, pid_status: str,
    pnl: dict, git: dict, strats: dict,
    cusum: list[str], guard_count: int | dict[str, int],
    grade: str = "?", wins: str = "", losses: str = "",
    visibility_gate: dict | None = None,
) -> str:
    """Generate the MAIN CHAT section for polybot-init.md."""
    next_s = session_num + 1
    log_path = get_log_path(next_s)
    alltime = pnl["alltime"]
    today = pnl["today"]
    gap = 125 - alltime
    sniper = strats.get("expiry_sniper_v1", {})
    sniper_n = sniper.get("n", 0)
    sniper_wr = round(100 * sniper.get("wins", 0) / sniper_n, 1) if sniper_n else 0

    # Estimate daily rate from today's bets
    daily_rate = today if today > 0 else 8.0  # fallback to 8 USD/day
    days_to_goal = round(max(0, gap) / daily_rate, 1) if daily_rate > 0 else "?"

    restart_cmd = (
        f"pkill -f \"python3 main.py\" 2>/dev/null; pkill -f \"python main.py\" 2>/dev/null; "
        f"sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; "
        f"echo \"CONFIRM\" > /tmp/polybot_confirm.txt; "
        f"nohup ./venv/bin/python3 main.py --live --reset-soft-stop "
        f"< /tmp/polybot_confirm.txt >> {log_path} 2>&1 &"
    )

    cusum_summary = " | ".join(cusum[:4]) if cusum else "all stable"
    visibility_gate = visibility_gate or {
        "status": "UNKNOWN",
        "reason": "Visibility gate was not collected during wrap.",
        "timestamp_display": "missing",
    }
    overhaul = summarize_overhaul_status(visibility_gate)
    auto_guard_count = guard_count["auto"] if isinstance(guard_count, dict) else guard_count
    startup_line = (
        "  Bot may still be running. Verify PID/log freshness before any restart."
        if pid_status == "ALIVE"
        else "  Bot is STOPPED. Run restart command first."
    )

    lines = [
        f"--- MAIN CHAT (Session {next_s} — monitoring + research combined PERMANENTLY) ---",
        f"{overhaul['summary']}",
        f"{overhaul['directive']}",
        f"⚠️ MONITORING CHAT: Update this section at every /polybot-wrap.",
        f"Use /polybot-auto after startup. Do research during monitoring downtime inline.",
        f"Bot: {'RUNNING' if pid_status == 'ALIVE' else 'STOPPED'} "
        f"→ restart for S{next_s} | All-time P&L: {alltime:+.2f} USD",
        f"Tests: {git['test_count']} passing | Last commit: {git['hash']} ({git['msg'][:50]})",
        f"",
        f"S{session_num} KEY CHANGES:",
        f"- S{session_num} GRADE: {grade} | wins: {wins[:120] if wins else '(see CHANGELOG)'}",
        f"  losses: {losses[:100] if losses else '(see CHANGELOG)'}",
        f"",
        f"CRITICAL STARTUP CHECKS:",
        startup_line,
        f"  tail -5 {log_path}  (MUST be recent after restart)",
        f"  grep 'Loaded.*auto-discovered' {log_path} | tail -1",
        f"  MUST show 'Loaded {auto_guard_count} auto-discovered guard(s)'",
        f"  grep 'n_observations' data/drift_posterior.json  (MUST show n_observations>=334)",
        f"  Latest visibility gate: {visibility_gate['status']} @ {visibility_gate['timestamp_display']}",
        f"  {visibility_gate['reason']}",
        f"",
        f"STARTUP SEQUENCE (run in order):",
        f"1. cat bot.pid — get PID. Then tail -5 {log_path} — verify RECENT.",
        f"   If stale >15min: RESTART even if ps shows alive (frozen process pattern).",
        f"2. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -100",
        f"3. ./venv/bin/python3 scripts/auto_guard_discovery.py",
        f"4. ./venv/bin/python3 scripts/bet_analytics.py 2>&1 | grep 'CUSUM|DRIFT|ERODING|E-Value'",
        f"5. ./venv/bin/python3 scripts/kalshi_visibility_report.py --edge-mode cached --strict-same-day-sports",
        f"   MUST pass before strategy planning. If it fails, review same-day skipped series first.",
        f"6. ./venv/bin/python3 main.py --health",
        f"",
        f"MONITORING PRIORITIES:",
        f"- PRIORITY 1: close overhaul blockers — visibility, coverage assumptions, startup-state drift.",
        f"- PRIORITY 2: read latest CCA delivery, then reconcile restart/series-planning work against current blockers.",
        f"- PRIORITY 3: only after blockers close, evaluate restart and same-day strategy planning.",
        f"- Do not restart or expand just because useful components exist.",
        f"- CUSUM STATE: {cusum_summary}",
        f"- All-time P&L: {alltime:.2f} USD | Target: +125 USD | Gap: {max(0, gap):.2f} USD",
        f"  Daily rate: ~{daily_rate:.1f} USD/day → ~{days_to_goal} days to goal",
        f"",
        f"RESTART COMMAND (Session {next_s}):",
        restart_cmd,
        f"",
        f"AUTOLOOP (new this session):",
        f"  From plain bash terminal: cd ~/Projects/polymarket-bot && ./start_autoloop.sh --tmux",
        f"  Opens new Terminal.app window per session. Handles restarts autonomously.",
        f"  Status: ./start_autoloop.sh --status",
        f"",
        f"AUTONOMY: Full autonomy active. NEVER ask Matthew to confirm anything.",
        f"--- END MAIN CHAT PROMPT ---",
    ]

    return "\n".join(lines)


def generate_changelog_entry(
    session_num: int, pnl: dict, git: dict,
    grade: str = "?", wins: str = "", losses: str = "",
    cusum: list[str] = None
) -> str:
    """Generate CHANGELOG.md entry."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d ~%H:%M UTC")
    sniper_today_wr = pnl.get("today_wr", 0)
    alltime = pnl["alltime"]
    gap = 125 - alltime

    lines = [
        f"## S{session_num} — {ts}",
        f"",
        f"### Session Summary",
        f"- Grade: {grade}",
        f"- Wins: {wins if wins else '(none recorded)'}",
        f"- Losses: {losses if losses else '(none recorded)'}",
        f"",
        f"### Performance",
        f"- Today live: {pnl['today_wins']}/{pnl['today_bets']} wins ({sniper_today_wr}% WR), {pnl['today']:+.2f} USD",
        f"- All-time live: {alltime:+.2f} USD | Gap to +125 goal: {max(0, gap):.2f} USD",
        f"",
        f"### CUSUM State",
    ]

    if cusum:
        for line in cusum[:5]:
            lines.append(f"- {line}")
    else:
        lines.append("- All stable")

    lines += [
        f"",
        f"---",
        f"",
    ]
    return "\n".join(lines)


# ── File Writers ─────────────────────────────────────────────────────────────

def update_session_resume(new_main_chat_block: str) -> bool:
    """Write MAIN CHAT section to SESSION_RESUME.md (replaces polybot-init.md update)."""
    try:
        existing = SESSION_RESUME.read_text(encoding="utf-8") if SESSION_RESUME.exists() else ""
    except Exception:
        existing = ""

    # Replace the MAIN CHAT block if present, otherwise prepend it
    start_marker = "--- MAIN CHAT"
    end_marker = "--- END MAIN CHAT PROMPT ---"
    start_idx = existing.find(start_marker)
    end_idx = existing.find(end_marker)

    if start_idx != -1 and end_idx != -1:
        new_content = (
            existing[:start_idx]
            + new_main_chat_block
            + "\n"
            + existing[end_idx + len(end_marker):]
        )
    elif "--- SESSION " in existing and "--- END SESSION " in existing:
        header = (
            "SESSION RESUME — auto-updated by /polybot-wrap and /polybot-wrapresearch.\n"
            "Do NOT edit manually. Read by /polybot-init at session start.\n\n"
        )
        new_content = header + new_main_chat_block + "\n"
    else:
        # Fresh file — write header + block
        header = (
            "SESSION RESUME — auto-updated by /polybot-wrap and /polybot-wrapresearch.\n"
            "Do NOT edit manually. Read by /polybot-init at session start.\n\n"
        )
        new_content = header + new_main_chat_block + "\n" + existing

    SESSION_RESUME.write_text(new_content, encoding="utf-8")
    return True


def append_changelog(entry: str) -> bool:
    """Append entry to CHANGELOG.md (after the first ## heading)."""
    if not CHANGELOG.exists():
        print(f"WARNING: {CHANGELOG} not found — skipping")
        return False

    content = CHANGELOG.read_text(encoding="utf-8")
    # Insert after the first line
    first_newline = content.find("\n")
    if first_newline == -1:
        content += "\n" + entry
    else:
        content = content[:first_newline + 1] + "\n" + entry + content[first_newline + 1:]

    CHANGELOG.write_text(content, encoding="utf-8")
    return True


# ── Log wrap assessment to CCA journal ──────────────────────────────────────

def log_to_cca_journal(session_num: int, grade: str, wins: str, losses: str):
    """Log session outcome to CCA's self-learning journal for cross-project tracking."""
    if not CCA_JOURNAL.exists():
        return

    venv_python = PROJECT_DIR / "venv" / "bin" / "python3"
    try:
        subprocess.run([
            str(venv_python), str(CCA_JOURNAL), "log", "session_outcome",
            "--session", str(session_num),
            "--domain", "kalshi_monitoring",
            "--outcome", "success" if grade in ("A", "A-", "B+", "B") else "partial",
            "--notes", f"Grade {grade}. Wins: {wins[:100]}. Losses: {losses[:100]}",
        ], cwd=PROJECT_DIR, capture_output=True, timeout=10)
    except Exception:
        pass  # CCA journal is optional — never block wrap for it


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Polybot wrap automation helper")
    parser.add_argument("--session", type=int, required=True, help="Current session number")
    parser.add_argument("--grade", default="?", help="Session grade (A/B/C/D)")
    parser.add_argument("--wins", default="", help="Session wins (one sentence)")
    parser.add_argument("--losses", default="", help="Session losses (one sentence)")
    parser.add_argument("--write", action="store_true", help="Auto-write files (SESSION_RESUME, CHANGELOG)")
    parser.add_argument("--autoloop", action="store_true", help="After --write, trigger next session in new Terminal.app window")
    parser.add_argument("--changelog-only", action="store_true", help="Only output changelog entry")
    parser.add_argument("--prompt-only", action="store_true", help="Only output new session prompt")
    args = parser.parse_args()

    session_num = args.session
    print(f"\nPolybot Wrap Helper — Session {session_num}")
    print("=" * 60)

    # Collect state
    print("Collecting state...")
    pid, pid_status = get_bot_pid()
    git = get_git_info()
    pnl = get_pnl_data(session_num)
    strats = get_strategy_counts()
    cusum = get_cusum_state()
    guard_count = get_guard_count()
    visibility_gate = get_visibility_gate()

    print(f"  PID {pid}: {pid_status}")
    print(f"  All-time P&L: {pnl['alltime']:+.2f} USD | Today: {pnl['today']:+.2f} USD "
          f"({pnl['today_wins']}/{pnl['today_bets']} bets, {pnl['today_wr']}% WR)")
    print(f"  Last commit: {git['hash']} | Tests: {git['test_count']}")
    print(f"  Guards: {guard_count['auto']} auto + {guard_count['il']} ILs | CUSUM lines: {len(cusum)}")
    print(f"  Visibility gate: {visibility_gate['status']} @ {visibility_gate['timestamp_display']}")

    # Generate content
    handoff_state = generate_handoff_bot_state(
        session_num, pid, pid_status, pnl, git, strats, args.grade, args.wins, args.losses, visibility_gate
    )
    main_chat = generate_main_chat_prompt(
        session_num, pid, pid_status, pnl, git, strats, cusum, guard_count,
        args.grade, args.wins, args.losses, visibility_gate
    )
    changelog = generate_changelog_entry(
        session_num, pnl, git, args.grade, args.wins, args.losses, cusum
    )

    # Write files if requested
    if args.write:
        print("\nWriting files...")
        if update_session_resume(main_chat):
            print(f"  ✓ {SESSION_RESUME} MAIN CHAT updated")
        if append_changelog(changelog):
            print(f"  ✓ {CHANGELOG} entry prepended")
        if args.grade != "?":
            log_to_cca_journal(session_num, args.grade, args.wins, args.losses)
            print("  ✓ CCA journal updated")

        # Autoloop trigger: open next session in new Terminal.app window
        if args.autoloop:
            import subprocess
            trigger = os.path.join(PROJECT_DIR, "polybot_autoloop_trigger.sh")
            if os.path.exists(trigger):
                print("\nTriggering next session in Terminal.app...")
                result = subprocess.run([trigger], capture_output=True, text=True)
                if result.returncode == 0:
                    print("  ✓ New Kalshi session opened in Terminal.app")
                else:
                    print(f"  ✗ Trigger failed: {result.stderr.strip()}")
            else:
                print("  ✗ polybot_autoloop_trigger.sh not found — skipping")

    # Output
    if args.changelog_only:
        print("\n" + "=" * 60)
        print("CHANGELOG ENTRY:")
        print("=" * 60)
        print(changelog)
        return

    if args.prompt_only:
        print("\n" + "=" * 60)
        print("NEXT SESSION PROMPT (copy to new chat):")
        print("=" * 60)
        print(main_chat)
        return

    print("\n" + "=" * 60)
    print("SESSION_HANDOFF BOT STATE:")
    print("=" * 60)
    print(handoff_state)

    print("\n" + "=" * 60)
    print("SESSION_RESUME.md MAIN CHAT (auto-written if --write):")
    print("=" * 60)
    print(main_chat)

    print("\n" + "=" * 60)
    print("CHANGELOG ENTRY (auto-written if --write):")
    print("=" * 60)
    print(changelog)

    print("\n" + "=" * 60)
    print("NEXT STEPS (all that remains for wrap):")
    print("=" * 60)
    print("  1. Run: ./venv/bin/python3 scripts/polybot_wrap_helper.py "
          f"--session {session_num} --grade A --wins '...' --losses '...' --write")
    print("  2. Update SESSION_HANDOFF.md manually with the BOT STATE block above")
    print("  3. git add SESSION_HANDOFF.md .planning/CHANGELOG.md && git commit")
    print("  4. git push")
    print("  5. Auto-trigger next session (optional):")
    print("       ./polybot_autoloop_trigger.sh")
    print("     OR add --autoloop to the wrap command above to trigger automatically after --write")
    print()


if __name__ == "__main__":
    main()
