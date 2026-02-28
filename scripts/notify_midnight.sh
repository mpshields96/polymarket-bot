#!/bin/bash
# PolyBot midnight daily P&L summary — Reminders app notification
# Fires once per day at midnight UTC. Kill with: kill $(cat /tmp/polybot_midnight.pid)
#
# Usage:
#   /Users/matthewshields/Projects/polymarket-bot/scripts/notify_midnight.sh &
#   echo $! > /tmp/polybot_midnight.pid

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
DB_PATH="$PROJECT_DIR/data/polybot.db"

while true; do
    # Sleep until next UTC midnight
    NOW_SEC=$(date -u +%s)
    # Seconds since midnight today
    SECS_SINCE_MIDNIGHT=$(( NOW_SEC % 86400 ))
    SECS_UNTIL_MIDNIGHT=$(( 86400 - SECS_SINCE_MIDNIGHT ))

    sleep "$SECS_UNTIL_MIDNIGHT"

    # Query DB for yesterday's P&L (UTC day that just ended)
    YESTERDAY=$(date -u -v-1d "+%Y-%m-%d" 2>/dev/null || date -u -d "yesterday" "+%Y-%m-%d")

    PNL_DATA=$("$VENV_PYTHON" - <<PYEOF 2>/dev/null
import sqlite3, sys
db = "$DB_PATH"
day = "$YESTERDAY"
try:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT is_paper, result, side, pnl_cents FROM trades WHERE date(timestamp, 'unixepoch') = ? AND result IS NOT NULL",
        (day,)
    ).fetchall()
    con.close()
    paper = [r for r in rows if r["is_paper"]]
    live  = [r for r in rows if not r["is_paper"]]
    paper_pnl = sum((r["pnl_cents"] or 0) for r in paper) / 100
    live_pnl  = sum((r["pnl_cents"] or 0) for r in live)  / 100
    paper_wins = sum(1 for r in paper if r["result"] == r["side"])
    live_wins  = sum(1 for r in live  if r["result"] == r["side"])
    print(f"paper_pnl={paper_pnl:.2f} paper_trades={len(paper)} paper_wins={paper_wins} live_pnl={live_pnl:.2f} live_trades={len(live)} live_wins={live_wins}")
except Exception as e:
    print(f"error={e}")
PYEOF
)

    # Parse key values (bash parameter expansion)
    PAPER_PNL=$(echo "$PNL_DATA" | grep -o 'paper_pnl=[^ ]*' | cut -d= -f2)
    PAPER_TRADES=$(echo "$PNL_DATA" | grep -o 'paper_trades=[^ ]*' | cut -d= -f2)
    PAPER_WINS=$(echo "$PNL_DATA" | grep -o 'paper_wins=[^ ]*' | cut -d= -f2)
    LIVE_PNL=$(echo "$PNL_DATA" | grep -o 'live_pnl=[^ ]*' | cut -d= -f2)
    LIVE_TRADES=$(echo "$PNL_DATA" | grep -o 'live_trades=[^ ]*' | cut -d= -f2)
    LIVE_WINS=$(echo "$PNL_DATA" | grep -o 'live_wins=[^ ]*' | cut -d= -f2)

    # Defaults in case of error
    PAPER_PNL="${PAPER_PNL:-?}"
    PAPER_TRADES="${PAPER_TRADES:-?}"
    PAPER_WINS="${PAPER_WINS:-?}"
    LIVE_PNL="${LIVE_PNL:-?}"
    LIVE_TRADES="${LIVE_TRADES:-?}"
    LIVE_WINS="${LIVE_WINS:-?}"

    SUMMARY="$YESTERDAY | Paper: \$${PAPER_PNL} (${PAPER_WINS}/${PAPER_TRADES}) | Live: \$${LIVE_PNL} (${LIVE_WINS}/${LIVE_TRADES})"
    TITLE="[PolyBot] Daily P&L — ${YESTERDAY}"

    osascript << APPLESCRIPT
tell application "Reminders"
    set newReminder to make new reminder at end of list "Reminders" with properties {name:"${TITLE}", remind me date:(current date), body:"${SUMMARY}"}
end tell
APPLESCRIPT

done
