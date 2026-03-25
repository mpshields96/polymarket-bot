#!/bin/bash
# start_autoloop.sh — Kalshi Main Chat Auto-Loop (Terminal.app)
#
# Opens a NEW Terminal.app window for each session, runs:
#   cd ~/Projects/polymarket-bot && cc "/kalshi-main"
# Waits for claude to exit (via sentinel file), closes the window, loops.
#
# Usage:
#   ./start_autoloop.sh              # Run the auto-loop (default: new window each session)
#   ./start_autoloop.sh --tmux       # Run inside a tmux window instead
#   ./start_autoloop.sh --status     # Show current loop state
#   ./start_autoloop.sh --dry-run    # Simulate without spawning sessions
#
# How it works:
#   1. Opens a fresh Terminal.app window titled "Polybot-Session-N"
#   2. Runs: cc --model sonnet "/kalshi-main" (init + monitoring loop)
#   3. Session runs bets + monitoring. After 1-2 context compactions,
#      titanium-context-monitor fires /polybot-wrap → claude exits cleanly.
#   4. Sentinel file detected → controller closes the window.
#   5. 30s cooldown → next iteration.
#
# Key differences from CCA autoloop:
#   - Terminal.app ALWAYS has accessibility permissions (no setup needed)
#   - Model fixed to sonnet (Max 5 plan)
#   - Sessions ~4x longer than CCA (Kalshi chat compacts more efficiently)
#   - Working directory: polymarket-bot (live money — conservative safety gates)
#   - Uses "cc" alias (= claude --dangerously-skip-permissions)
#
# Safety:
#   - Max 50 iterations (override: POLYBOT_AUTOLOOP_MAX=N)
#   - 3 consecutive crashes = auto-stop + alert
#   - 3 consecutive short sessions (<60s) = auto-stop (broken state)
#   - 5-min cooldown on rate limit (exit 2 or 75)
#   - 30s normal cooldown between sessions
#   - Never spawns more than 1 claude session at a time (PID check)
#   - Bot health check before each iteration
#   - Always unsets ANTHROPIC_API_KEY (Max subscription auth only)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_DIR="/Users/matthewshields/Projects/polymarket-bot"
LOG_FILE="$HOME/.polybot-autoloop.log"
STATE_FILE="$HOME/.polybot-autoloop-state.json"

MAX_ITERATIONS=${POLYBOT_AUTOLOOP_MAX:-50}
COOLDOWN=${POLYBOT_AUTOLOOP_COOLDOWN:-30}
MIN_SESSION_SECS=60
MAX_CONSECUTIVE_CRASHES=3
MAX_CONSECUTIVE_SHORT=3
RATE_LIMIT_COOLDOWN=300
MODEL="sonnet"

iteration=0
total_sessions=0
total_crashes=0
consecutive_crashes=0
consecutive_short=0

unset ANTHROPIC_API_KEY
cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_event() {
    local event="$1"
    local data="${2:-{}}"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "{\"ts\":\"$ts\",\"event\":\"$event\",\"data\":$data}" >> "$LOG_FILE" 2>/dev/null || true
}

save_state() {
    cat > "$STATE_FILE" <<STATEJSON
{
  "iteration": $iteration,
  "total_sessions": $total_sessions,
  "total_crashes": $total_crashes,
  "consecutive_crashes": $consecutive_crashes,
  "consecutive_short": $consecutive_short,
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
STATEJSON
}

check_bot_alive() {
    local pid
    pid=$(cat "$PROJECT_DIR/bot.pid" 2>/dev/null || echo "0")
    if [ "$pid" != "0" ] && kill -0 "$pid" 2>/dev/null; then
        echo "  Bot PID $pid — ALIVE"
        return 0
    else
        echo "  WARNING: Bot not running (PID=$pid) — new session will handle restart"
        return 1
    fi
}

get_handoff_line() {
    grep -E "All-time P&L|Bot:|Last commit:" "$PROJECT_DIR/SESSION_HANDOFF.md" 2>/dev/null | head -3 || echo "  (no handoff summary)"
}

check_no_other_claude() {
    # Skip check in dry-run (controller is not spawning sessions)
    [ "$DRY_RUN" = true ] && return 0
    local count
    count=$(ps ax -o command 2>/dev/null | grep "claude.*dangerously-skip" | grep -v grep | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        echo "BLOCKED: $count claude session(s) already running."
        echo "This script must be run from a plain bash terminal, not from inside claude."
        echo "Close active claude sessions first, then retry."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

DRY_RUN=false
TMUX_MODE=false

case "${1:-}" in
    --status)
        echo "Polybot Auto-Loop Status:"
        if [ -f "$STATE_FILE" ]; then
            cat "$STATE_FILE"
        else
            echo "No state file. Loop has not run yet."
        fi
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Last 5 log events:"
            tail -5 "$LOG_FILE" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        print(f\"  {e['ts']}  {e['event']}  {e.get('data',{})}\")
    except:
        print(f'  {line.strip()}')
" 2>/dev/null || tail -5 "$LOG_FILE"
        fi
        exit 0
        ;;
    --tmux)
        TMUX_MODE=true
        SESSION="polybot"
        WINDOW="autoloop"
        if ! tmux has-session -t "$SESSION" 2>/dev/null; then
            tmux new-session -d -s "$SESSION" -n main
        fi
        if tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -q "^${WINDOW}$"; then
            echo "Autoloop tmux window already running."
            echo "Attach: tmux attach -t $SESSION:$WINDOW"
            exit 1
        fi
        tmux new-window -t "$SESSION" -n "$WINDOW" \
            "cd '$PROJECT_DIR' && unset ANTHROPIC_API_KEY && '$PROJECT_DIR/start_autoloop.sh'; echo 'Loop exited. Press Enter.'; read"
        echo "Polybot autoloop started: tmux attach -t $SESSION:$WINDOW"
        echo "Status: ./start_autoloop.sh --status"
        exit 0
        ;;
    --dry-run)
        DRY_RUN=true
        echo "DRY RUN — no sessions will be spawned"
        ;;
    --help|-h)
        grep "^#" "$0" | head -40 | sed 's/^# //' | sed 's/^#//'
        exit 0
        ;;
    "") : ;;
    *)
        echo "Unknown option: $1. Run --help for usage."
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

echo "========================================================"
echo "  Polybot Auto-Loop"
echo "  Max iterations: $MAX_ITERATIONS | Cooldown: ${COOLDOWN}s"
echo "  Model: $MODEL | Project: $PROJECT_DIR"
echo "  Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'Terminal.app new window')"
echo "========================================================"
echo ""

if ! command -v claude &>/dev/null; then
    echo "BLOCKED: claude not found on PATH."
    exit 1
fi
echo "  claude: $(which claude)"
echo "  cc alias: claude --dangerously-skip-permissions (from ~/.zshrc)"
echo ""

check_no_other_claude

echo "SESSION_HANDOFF:"
get_handoff_line
echo ""
check_bot_alive
echo ""

log_event "loop_started" "{\"max_iterations\":$MAX_ITERATIONS,\"cooldown\":$COOLDOWN,\"model\":\"$MODEL\",\"dry_run\":$DRY_RUN}"

# ---------------------------------------------------------------------------
# Cleanup on interrupt
# ---------------------------------------------------------------------------

cleanup_and_exit() {
    echo ""
    echo "Loop interrupted at iteration $iteration."
    save_state
    log_event "loop_interrupted" "{\"iteration\":$iteration}"
    # Clean up any orphaned temp files
    rm -f /tmp/polybot-autoloop-sentinel-$$-* /tmp/polybot-autoloop-wrapper-$$-* /tmp/polybot-autoloop-prompt-$$-* 2>/dev/null
    exit 0
}
trap cleanup_and_exit INT TERM

# ---------------------------------------------------------------------------
# Single Session: new Terminal.app window
# ---------------------------------------------------------------------------

run_terminal_session() {
    local iter="$1"
    local window_title="Polybot-Session-${iter}"
    local sentinel="/tmp/polybot-autoloop-sentinel-$$-${iter}"
    local wrapper="/tmp/polybot-autoloop-wrapper-$$-${iter}.sh"
    rm -f "$sentinel"

    # Build wrapper script that runs in the new window
    cat > "$wrapper" << WRAPEOF
#!/bin/bash
# Polybot autoloop wrapper — session $iter
printf '\e]0;${window_title}\a'
cd "$PROJECT_DIR"
unset ANTHROPIC_API_KEY

echo "========================================================"
echo "  Polybot Auto-Loop — Session $iter"
echo "  Model: $MODEL"
echo "  Started: \$(date -u '+%Y-%m-%d %H:%M UTC')"
echo "========================================================"
echo ""

# Run claude with /kalshi-main startup trigger
# --dangerously-skip-permissions = autonomous, no confirmation prompts
claude --dangerously-skip-permissions --model "$MODEL" "/kalshi-main"
CLAUDE_EXIT=\$?

echo \$CLAUDE_EXIT > "$sentinel"
echo ""
echo "Session $iter complete (exit=\$CLAUDE_EXIT)."
echo "Controller will close this window. Do NOT close manually."
exit 0
WRAPEOF
    chmod +x "$wrapper"

    echo "Opening Terminal.app window: $window_title..."
    osascript -e "tell application \"Terminal\" to do script \"'$wrapper'\"" >/dev/null 2>&1

    # Poll for sentinel (session exit)
    local wait_count=0
    while [ ! -f "$sentinel" ]; do
        sleep 3
        wait_count=$((wait_count + 3))
        # Log alive every 5 min
        if [ $((wait_count % 300)) -eq 0 ]; then
            log_event "session_alive" "{\"iteration\":$iter,\"elapsed\":$wait_count}"
        fi
    done

    local exit_code
    exit_code=$(cat "$sentinel")

    # Wait for shell to fully exit before closing (avoids "terminate?" dialog)
    sleep 3

    # Close the Terminal.app window
    osascript -e "tell application \"Terminal\"
        set targetTitle to \"$window_title\"
        repeat with w in windows
            repeat with t in tabs of w
                if name of t contains targetTitle then
                    close w saving no
                    return
                end if
            end repeat
        end repeat
    end tell" &>/dev/null 2>&1 || true

    # Handle "terminate?" dialog if it appeared
    sleep 0.5
    osascript -e 'tell application "System Events"
        tell process "Terminal"
            if exists sheet 1 of front window then
                try
                    click button "Terminate" of sheet 1 of front window
                end try
            end if
        end tell
    end tell' &>/dev/null 2>&1 || true

    # Cleanup
    rm -f "$sentinel" "$wrapper"

    echo "$exit_code"
}

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

while [ $iteration -lt $MAX_ITERATIONS ]; do
    iteration=$((iteration + 1))

    echo "========================================================"
    echo "  ITERATION $iteration / $MAX_ITERATIONS  |  $(date -u '+%H:%M UTC')"
    echo "========================================================"

    check_bot_alive || true
    echo ""

    log_event "iteration_start" "{\"iteration\":$iteration}"
    start_ts=$(date +%s)

    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN: would open Terminal.app window and run:"
        echo "  cc --model $MODEL \"/kalshi-main\""
        echo "Simulating 5s session..."
        sleep 5
        exit_code=0
    else
        exit_code=$(run_terminal_session "$iteration")
    fi

    end_ts=$(date +%s)
    duration=$((end_ts - start_ts))
    total_sessions=$((total_sessions + 1))

    echo "Session $iteration complete: exit=$exit_code  duration=${duration}s"
    log_event "iteration_complete" "{\"iteration\":$iteration,\"exit_code\":$exit_code,\"duration\":$duration}"

    # Crash tracking (rate limits are expected, not crashes)
    if [ $exit_code -ne 0 ] && [ $exit_code -ne 2 ] && [ $exit_code -ne 75 ]; then
        total_crashes=$((total_crashes + 1))
        consecutive_crashes=$((consecutive_crashes + 1))
        echo "WARNING: Session crash (exit=$exit_code, consecutive: $consecutive_crashes/$MAX_CONSECUTIVE_CRASHES)"
        log_event "session_crash" "{\"exit_code\":$exit_code,\"consecutive\":$consecutive_crashes}"
    else
        consecutive_crashes=0
    fi

    # Short session tracking
    if [ $duration -lt $MIN_SESSION_SECS ]; then
        consecutive_short=$((consecutive_short + 1))
        echo "WARNING: Short session ${duration}s (consecutive: $consecutive_short/$MAX_CONSECUTIVE_SHORT)"
        log_event "session_short" "{\"duration\":$duration,\"consecutive\":$consecutive_short}"
    else
        consecutive_short=0
    fi

    save_state

    # Stop conditions
    if [ $consecutive_crashes -ge $MAX_CONSECUTIVE_CRASHES ]; then
        echo "STOPPING: $MAX_CONSECUTIVE_CRASHES consecutive crashes. Investigate before restarting."
        log_event "loop_stopped" "{\"reason\":\"consecutive_crashes\"}"
        break
    fi

    if [ $consecutive_short -ge $MAX_CONSECUTIVE_SHORT ]; then
        echo "STOPPING: $MAX_CONSECUTIVE_SHORT consecutive short sessions. Check SESSION_HANDOFF.md."
        log_event "loop_stopped" "{\"reason\":\"consecutive_short_sessions\"}"
        break
    fi

    # Cooldown before next session
    if [ $iteration -lt $MAX_ITERATIONS ]; then
        if [ $exit_code -eq 2 ] || [ $exit_code -eq 75 ]; then
            echo "Rate limit (exit=$exit_code). Extended cooldown: ${RATE_LIMIT_COOLDOWN}s..."
            log_event "rate_limit_cooldown" "{\"cooldown\":$RATE_LIMIT_COOLDOWN}"
            sleep $RATE_LIMIT_COOLDOWN
        else
            echo "Cooldown: ${COOLDOWN}s..."
            sleep $COOLDOWN
        fi
    fi
    echo ""
done

echo ""
echo "========================================================"
echo "  Polybot Auto-Loop Finished"
echo "  Iterations: $iteration | Sessions: $total_sessions | Crashes: $total_crashes"
echo "========================================================"

save_state
log_event "loop_finished" "{\"iterations\":$iteration,\"sessions\":$total_sessions,\"crashes\":$total_crashes}"
