#!/bin/bash
# polybot_autoloop_trigger.sh — Opens a new Terminal.app window running /kalshi-main
# Called as the FINAL step of /polybot-wrap to chain the next session automatically.
#
# Lessons from CCA autoloop (S134):
#   - Always use full path for claude binary (PATH not guaranteed in new window)
#   - Always open a NEW window (never paste into existing session)
#   - Dry-run mode for testing without actually opening Terminal.app
#   - Log trigger events for audit trail

set -euo pipefail

PROJ="/Users/matthewshields/Projects/polymarket-bot"
CLAUDE_BIN="$HOME/.local/bin/claude"
TRIGGER_LOG="$HOME/.polybot-autoloop-trigger.jsonl"
DRY_RUN=false

# Parse args
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --check)
            echo "Checking readiness..."
            if [ -x "$CLAUDE_BIN" ]; then
                echo "  claude binary: OK ($CLAUDE_BIN)"
            else
                echo "  claude binary: FAIL (not found at $CLAUDE_BIN)"
                exit 1
            fi
            if [ -d "$PROJ" ]; then
                echo "  project dir: OK"
            else
                echo "  project dir: FAIL ($PROJ missing)"
                exit 1
            fi
            echo "  Ready to trigger."
            exit 0
            ;;
    esac
done

log_event() {
    local event="$1"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "{\"ts\":\"$ts\",\"event\":\"$event\"}" >> "$TRIGGER_LOG" 2>/dev/null || true
}

# Safety: verify claude binary exists
if [ ! -x "$CLAUDE_BIN" ]; then
    echo "ERROR: claude binary not found at $CLAUDE_BIN"
    log_event "trigger_failed_no_binary"
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: would open Terminal.app and run:"
    echo "  cd $PROJ && $CLAUDE_BIN --dangerously-skip-permissions '/kalshi-main'"
    log_event "trigger_dry_run"
    exit 0
fi

echo "Opening new Terminal.app window for /kalshi-main..."
log_event "trigger_fired"

# Open new Terminal.app window with correct PATH + project dir + claude command
# Single-quoted HEREDOC so $CLAUDE_BIN/$PROJ expand NOW (shell) not inside osascript
osascript <<OSASCRIPT
tell application "Terminal"
    activate
    do script "export PATH='$HOME/.local/bin:\$PATH'; cd '$PROJ'; '$CLAUDE_BIN' --dangerously-skip-permissions '/kalshi-main'"
end tell
OSASCRIPT

log_event "trigger_window_opened"
echo "New Kalshi session started in Terminal.app."
