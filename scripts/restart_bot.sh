#!/bin/bash
# restart_bot.sh — safe bot restart with correct paths and instance guard
#
# Usage: bash scripts/restart_bot.sh
# Requires: bot.pid must exist in project root, venv must be at ./venv/
#
# Always use this instead of manually running kill/pkill to ensure:
# - Correct full venv python path (not bare 'python')
# - pkill targets ALL instances (not just the most recent)
# - bot.pid is cleaned before restart
# - Exactly 1 instance verified after start

set -euo pipefail
cd "$(dirname "$0")/.."
PROJ="$(pwd)"
VENV_PYTHON="$PROJ/venv/bin/python"
LOG="/tmp/polybot_session21.log"

echo "=== polymarket-bot restart ==="
echo "Project: $PROJ"

# 1. Kill all existing instances
echo "[1/4] Killing existing instances..."
pkill -f "python main.py" 2>/dev/null || true
sleep 3

# 2. Clean stale PID file
echo "[2/4] Cleaning bot.pid..."
rm -f "$PROJ/bot.pid"

# 3. Start fresh
echo "[3/4] Starting bot..."
echo "CONFIRM" | nohup "$VENV_PYTHON" "$PROJ/main.py" --live >> "$LOG" 2>&1 &
sleep 6

# 4. Verify exactly ONE instance
echo "[4/4] Verifying single instance..."
COUNT=$(ps aux | grep "[m]ain.py" | wc -l)
if [ "$COUNT" -eq 1 ]; then
    PID=$(ps aux | grep "[m]ain.py" | awk '{print $2}')
    echo "OK — bot running (PID $PID)"
    cat "$PROJ/bot.pid" 2>/dev/null && echo ""
elif [ "$COUNT" -eq 0 ]; then
    echo "ERROR — bot failed to start. Check $LOG"
    exit 1
else
    echo "WARNING — $COUNT instances detected (orphan guard should fire). Waiting 10s..."
    sleep 10
    COUNT2=$(ps aux | grep "[m]ain.py" | wc -l)
    if [ "$COUNT2" -eq 1 ]; then
        echo "OK — orphan guard cleaned up. Single instance running."
    else
        echo "ERROR — Multiple instances still running. Check log."
        exit 1
    fi
fi

echo ""
echo "Log: tail -f $LOG"
