#!/usr/bin/env bash
# .claude/hooks/verify_revert.sh — Pattern 2: VERIFY-REVERT loop
#
# PURPOSE:
#   PostToolUse hook. After any Edit/Write to a DANGER ZONE file:
#   1. Runs the full test suite
#   2. If tests FAIL: git checkout HEAD -- <file> (auto-revert the change)
#   3. Logs all actions to /tmp/polybot_verify_revert.log
#
# EXIT CODES:
#   Always exits 0 (PostToolUse hooks can't block, only report)
#
# DANGER ZONES: same 6 files as danger_zone_guard.sh

set -uo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PROJ_ROOT}/venv/bin/python3"
LOG="/tmp/polybot_verify_revert.log"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] $1" | tee -a "$LOG" >&2; }

DANGER_ZONE_FILES=(
    "src/execution/live.py"
    "src/risk/kill_switch.py"
    "src/risk/sizing.py"
    "src/auth/kalshi_auth.py"
    "src/platforms/kalshi.py"
    "main.py"
)

# ── Read tool input from stdin ────────────────────────────────────────
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only act on Edit/Write tools
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
    exit 0
fi

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# ── Check if file is in danger zone ──────────────────────────────────
IN_DANGER_ZONE=false
for dz_file in "${DANGER_ZONE_FILES[@]}"; do
    if [[ "$FILE_PATH" == *"$dz_file"* ]]; then
        IN_DANGER_ZONE=true
        break
    fi
done

if [[ "$IN_DANGER_ZONE" != "true" ]]; then
    exit 0
fi

log "VERIFY-REVERT: Edit detected on DANGER ZONE file: $FILE_PATH"

# ── Run test suite ────────────────────────────────────────────────────
cd "$PROJ_ROOT"
TEST_OUTPUT=$("$PYTHON" -m pytest tests/ -q --tb=short 2>&1)
TEST_EXIT=$?

if [[ $TEST_EXIT -eq 0 ]]; then
    PASSED=$(echo "$TEST_OUTPUT" | grep -oE '[0-9]+ passed' | head -1)
    log "VERIFY-REVERT: Tests PASSED ($PASSED) — change to $FILE_PATH accepted"
    exit 0
fi

# ── Tests failed — auto-revert ────────────────────────────────────────
log "VERIFY-REVERT: Tests FAILED after editing $FILE_PATH"
log "VERIFY-REVERT: Test output summary:"
echo "$TEST_OUTPUT" | grep -E "FAILED|ERROR|error" | head -10 | while read -r line; do
    log "  $line"
done

# Revert the file
RELATIVE_PATH="${FILE_PATH#$PROJ_ROOT/}"
if git -C "$PROJ_ROOT" checkout HEAD -- "$RELATIVE_PATH" 2>/dev/null; then
    log "VERIFY-REVERT: AUTO-REVERTED $RELATIVE_PATH to HEAD"
    log "VERIFY-REVERT: Fix the tests, then re-apply your change."
else
    log "VERIFY-REVERT: WARNING — could not auto-revert $RELATIVE_PATH (not tracked by git?)"
fi

exit 0
