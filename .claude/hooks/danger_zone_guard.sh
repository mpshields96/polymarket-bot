#!/usr/bin/env bash
# .claude/hooks/danger_zone_guard.sh — TIER 1 Danger Zone PreToolUse guard
#
# PURPOSE:
#   Intercepts Edit/Write tool calls targeting TIER 1 DANGER ZONE files.
#   If the target file is in the danger zone, runs the full test suite first.
#   If tests fail: exits 2 (hard-blocks the edit in Claude Code).
#   If tests pass: exits 0 (allows the edit to proceed).
#
# HOW IT'S CALLED:
#   Claude Code PreToolUse hook. Tool input JSON is read from stdin.
#   The hook extracts "file_path" from the JSON.
#
# EXIT CODES:
#   0 = allow (file not in danger zone, OR tests passed)
#   2 = hard-block (file is in danger zone AND tests failed)
#
# TIER 1 FILES (immediate money-loss risk):
#   src/execution/live.py       — real order placement, all execution guards
#   src/risk/kill_switch.py     — all hard/soft stops and thresholds
#   src/risk/sizing.py          — Kelly calculation and stage caps

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PROJ_ROOT}/venv/bin/python3"

# ── TIER 1 DANGER ZONE file list ─────────────────────────────────────
# These files require full test suite pass before any edit is allowed.
# If adding a file here, also add it to BOUNDS.md.

DANGER_ZONE_FILES=(
    "src/execution/live.py"
    "src/risk/kill_switch.py"
    "src/risk/sizing.py"
    "src/auth/kalshi_auth.py"
    "src/platforms/kalshi.py"
    "main.py"
)

# ── Read file_path from tool input JSON (stdin) ───────────────────────

TOOL_INPUT="$(cat)"
FILE_PATH="$(echo "$TOOL_INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
# Edit tool: file_path key
# Write tool: file_path key
print(data.get('file_path', ''))
" 2>/dev/null || echo "")"

if [[ -z "$FILE_PATH" ]]; then
    # Can't determine file path — allow (fail open, don't block legitimate edits)
    exit 0
fi

# Normalize to relative path for comparison
REL_PATH="${FILE_PATH#$PROJ_ROOT/}"

# ── Check if file is in danger zone ──────────────────────────────────

IN_DANGER_ZONE=0
for dz_file in "${DANGER_ZONE_FILES[@]}"; do
    if [[ "$REL_PATH" == "$dz_file" ]] || [[ "$FILE_PATH" == *"$dz_file" ]]; then
        IN_DANGER_ZONE=1
        break
    fi
done

if [[ $IN_DANGER_ZONE -eq 0 ]]; then
    # Not a danger zone file — allow immediately
    exit 0
fi

# ── Danger zone file detected — run test suite ────────────────────────

echo "" >&2
echo "⚠️  DANGER ZONE: $REL_PATH" >&2
echo "   Running test suite before allowing edit..." >&2
echo "" >&2

cd "$PROJ_ROOT"

check_iron_laws() {
    local warnings=0

    echo "" >&2
    echo "── IRON LAWS ADVISORY CHECK ────────────────────────────────────" >&2

    # LAW 3: expiry_sniper slippage guard must be present in main.py
    # (price_guard_min=1 is intentional for NO-side bets; the real guard is
    # the _MAX_SLIPPAGE_CENTS pre-execution check added in S81)
    if ! grep -q "_MAX_SLIPPAGE_CENTS" "$PROJ_ROOT/main.py" 2>/dev/null; then
        echo "WARNING [LAW 3]: _MAX_SLIPPAGE_CENTS slippage guard missing from main.py" >&2
        echo "  Expected pre-execution check: if _live_price < signal.price_cents - _MAX_SLIPPAGE_CENTS" >&2
        echo "  Trade 2786 (YES@86c, -19.78 USD) was caused by missing this guard." >&2
        warnings=$((warnings + 1))
    fi

    # LAW 5: no hardcoded credentials in .py files
    local cred_hits
    cred_hits=$(grep -rn "BEGIN RSA PRIVATE KEY\|KALSHI_API_KEY_ID\s*=\s*\"[^\"]\|sk-ant-" \
        "$PROJ_ROOT/src" "$PROJ_ROOT/main.py" 2>/dev/null | grep -v "\.pyc" || true)
    if [[ -n "$cred_hits" ]]; then
        echo "WARNING [LAW 5]: Possible hardcoded credentials detected:" >&2
        echo "$cred_hits" >&2
        warnings=$((warnings + 1))
    fi

    # LAW 2: kill_switch HARD_MAX_TRADE_USD must be 20.00
    local hard_max
    hard_max=$(grep -m1 "HARD_MAX_TRADE_USD\s*=" "$PROJ_ROOT/src/risk/kill_switch.py" \
        2>/dev/null | grep -oE "[0-9]+\.[0-9]+" || echo "NOT_FOUND")
    if [[ "$hard_max" != "20.00" ]]; then
        echo "WARNING [LAW 2]: HARD_MAX_TRADE_USD=$hard_max in kill_switch.py" >&2
        echo "  Expected 20.00. Verify this change is intentional." >&2
        warnings=$((warnings + 1))
    fi

    if [[ $warnings -eq 0 ]]; then
        echo "All Iron Laws checks passed." >&2
    else
        echo "$warnings warning(s) above — advisory only, edit is NOT blocked." >&2
    fi
    echo "────────────────────────────────────────────────────────────────" >&2
    echo "" >&2
}

if "$PYTHON" -m pytest tests/ -q --tb=short 2>&1 >&2; then
    echo "" >&2
    echo "✓ Tests passed — edit to $REL_PATH is allowed." >&2
    check_iron_laws
    echo "" >&2
    exit 0
else
    echo "" >&2
    echo "✗ BLOCKED: Tests failed." >&2
    echo "  Fix failing tests before editing $REL_PATH." >&2
    echo "  This file is a TIER 1 DANGER ZONE (see BOUNDS.md)." >&2
    echo "" >&2
    exit 2
fi
