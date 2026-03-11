#!/bin/bash
# restart_bot.sh — safe bot restart with correct paths and instance guard
#
# Usage: bash scripts/restart_bot.sh [SESSION_NUM]
# Example: bash scripts/restart_bot.sh 52
#
# If SESSION_NUM is omitted, auto-generates from current date+time.
#
# Always use this instead of manually running kill/pkill to ensure:
# - Correct full venv python3 path (not bare 'python')
# - pkill targets ALL instances (not just the most recent)
# - bot.pid is cleaned before restart
# - Exactly 1 instance verified after start
# - CONFIRM input via temp file (nohup drops piped stdin — see CLAUDE.md Gotchas)
# - --reset-soft-stop clears stale consecutive cooling at restart

set -uo pipefail

# SAFETY CHECK: require explicit session number to prevent accidental restarts
# Usage: bash scripts/restart_bot.sh 52
if [ -z "${1:-}" ] || [[ "${1}" == --* ]]; then
    echo "Usage: bash scripts/restart_bot.sh SESSION_NUM"
    echo "Example: bash scripts/restart_bot.sh 52"
    echo ""
    echo "SESSION_NUM is required to prevent accidental bot restarts."
    echo "It determines the log path: /tmp/polybot_sessionNN.log"
    exit 1
fi

cd "$(dirname "$0")/.."
PROJ="$(pwd)"
VENV_PYTHON="$PROJ/venv/bin/python3"
CONFIRM_FILE="/tmp/polybot_confirm.txt"
SESSION="$1"
LOG="/tmp/polybot_session${SESSION}.log"

echo "=== polymarket-bot restart ==="
echo "Project:  $PROJ"
echo "Log:      $LOG"
echo "Python:   $VENV_PYTHON"

# Verify venv python exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR — venv python3 not found at $VENV_PYTHON"
    exit 1
fi

# 1. Kill all existing instances
echo ""
echo "[1/5] Killing existing instances..."
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "python main.py" 2>/dev/null || true
sleep 3
# Hard kill any that survive
kill -9 "$(cat "$PROJ/bot.pid" 2>/dev/null)" 2>/dev/null || true

# 2. Clean stale PID file
echo "[2/5] Cleaning bot.pid..."
rm -f "$PROJ/bot.pid"

# 3. Write CONFIRM to temp file (nohup drops piped stdin — critical gotcha)
echo "[3/5] Preparing CONFIRM input..."
echo "CONFIRM" > "$CONFIRM_FILE"

# 4. Start fresh (use < redirect, NOT pipe, for nohup stdin)
echo "[4/5] Starting bot..."
nohup "$VENV_PYTHON" "$PROJ/main.py" --live --reset-soft-stop < "$CONFIRM_FILE" >> "$LOG" 2>&1 &
sleep 8

# 5. Verify exactly ONE instance
echo "[5/5] Verifying single instance..."
COUNT=$(ps aux | grep "[m]ain.py" | grep -v grep | wc -l | tr -d ' ')
if [ "$COUNT" -eq 1 ]; then
    PID=$(ps aux | grep "[m]ain.py" | grep -v grep | awk '{print $2}')
    echo "OK — bot running (PID $PID)"
    if [ -f "$PROJ/bot.pid" ]; then
        echo "bot.pid: $(cat "$PROJ/bot.pid")"
    fi
elif [ "$COUNT" -eq 0 ]; then
    echo "ERROR — bot failed to start. Check $LOG"
    echo "Last 20 lines:"
    tail -20 "$LOG" 2>/dev/null
    exit 1
else
    echo "WARNING — $COUNT instances detected. Waiting 10s for orphan guard..."
    sleep 10
    COUNT2=$(ps aux | grep "[m]ain.py" | grep -v grep | wc -l | tr -d ' ')
    if [ "$COUNT2" -eq 1 ]; then
        echo "OK — orphan guard cleaned up. Single instance running."
    else
        echo "ERROR — Multiple instances still running. Check log."
        exit 1
    fi
fi

echo ""
echo "Monitor: tail -f $LOG"
echo "Status:  $VENV_PYTHON $PROJ/main.py --health"
echo "Report:  $VENV_PYTHON $PROJ/main.py --report"
