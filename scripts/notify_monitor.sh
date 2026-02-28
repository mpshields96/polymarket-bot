#!/bin/bash
# Bot monitoring reminder — sends macOS notifications at set intervals
# Kill with: kill $(cat /tmp/polybot_notify.pid)

INTERVAL_SEC=900   # 15 min for first hour, then changes to 30 min
START_TIME=$(date +%s)
COUNT=0

while true; do
    COUNT=$((COUNT + 1))
    NOW=$(date +%s)
    ELAPSED=$(( (NOW - START_TIME) / 60 ))

    # After first hour, switch to 30-min intervals
    if [ $ELAPSED -ge 60 ]; then
        INTERVAL_SEC=1800
    fi

    osascript -e "display notification \"Type 'status' in Claude Code to check\" with title \"🤖 Polymarket Bot — Check #${COUNT} (${ELAPSED}min elapsed)\" sound name \"Ping\""

    sleep $INTERVAL_SEC
done
