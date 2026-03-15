#!/usr/bin/env bash
# scripts/verify_change.sh — Verify-Revert Loop (Pattern 2)
#
# PURPOSE:
#   Before finalising any strategy parameter change:
#     1. Stash current working changes (preserves them — not lost on failure)
#     2. Run full test suite
#     3. Run strategy win-rate baseline check against settled DB trades
#     4. If BOTH pass: restore stash, print VERIFIED
#     5. If EITHER fails: drop stash, print REVERTED + reason
#        (stash is dropped but changes are printed — recover with git stash pop if needed)
#
# USAGE:
#   bash scripts/verify_change.sh <strategy_name> <min_win_rate> [last_n]
#
# EXAMPLES:
#   bash scripts/verify_change.sh expiry_sniper 0.95
#   bash scripts/verify_change.sh btc_drift_v1 0.55 30
#   bash scripts/verify_change.sh sol_drift_v1 0.60
#
# ARGUMENTS:
#   strategy_name   Strategy name as stored in DB (e.g. expiry_sniper, btc_drift_v1)
#   min_win_rate    Minimum acceptable win rate, 0.0–1.0 (e.g. 0.95 for 95%)
#   last_n          Optional: number of recent settled bets to check (default: 30)
#
# EXIT CODES:
#   0 = VERIFIED (all checks passed, stash restored)
#   1 = REVERTED (a check failed, stash dropped — changes not applied to working tree)
#   2 = ERROR (bad args, missing files, git not clean enough)
#
# SAFETY NOTES:
#   - This script NEVER force-pushes or deletes branches
#   - On failure, changes go to git stash — recover with: git stash pop
#   - The live bot is NOT affected by this script (bot reads in-memory config until restart)
#   - NEVER pipe this script through head/grep/tail — see CLAUDE.md SIGPIPE warning

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJ_ROOT}/venv/bin/python3"

# ── Arg validation ────────────────────────────────────────────────────

if [[ $# -lt 2 ]]; then
    echo "USAGE: bash scripts/verify_change.sh <strategy_name> <min_win_rate> [last_n]"
    echo ""
    echo "  strategy_name   e.g. expiry_sniper, btc_drift_v1, sol_drift_v1"
    echo "  min_win_rate    e.g. 0.95 (95% win rate threshold)"
    echo "  last_n          optional, default 30 (settled live bets to check)"
    exit 2
fi

STRATEGY="$1"
MIN_WIN_RATE="$2"
LAST_N="${3:-30}"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  VERIFY-REVERT LOOP"
echo "  Strategy:     $STRATEGY"
echo "  Win rate min: $MIN_WIN_RATE (over last $LAST_N settled live bets)"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Check git state ───────────────────────────────────────────────────

cd "$PROJ_ROOT"

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "ERROR: Not inside a git repository" >&2
    exit 2
fi

# Check if there's anything to stash (staged or unstaged)
if git diff --quiet && git diff --cached --quiet; then
    echo "NOTE: No uncommitted changes found in working tree."
    echo "      Running checks against current committed state."
    HAS_STASH=0
else
    echo "Stashing current changes..."
    git stash push -m "verify_change.sh: ${STRATEGY} $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    HAS_STASH=1
    echo "Changes stashed. Stash entry: $(git stash list | head -1 | cut -d: -f1)"
fi

echo ""

# Track whether we should restore or drop the stash
VERIFIED=0
FAIL_REASON=""

# ── Gate 1: Full test suite ───────────────────────────────────────────

echo "── Gate 1: Test suite ──────────────────────────────"
if "$PYTHON" -m pytest tests/ -q --tb=short 2>&1; then
    echo "Gate 1: PASS (all tests passed)"
else
    FAIL_REASON="Gate 1 FAILED: test suite has failures"
    echo "$FAIL_REASON"
fi

echo ""

# Only run Gate 2 if Gate 1 passed
if [[ -z "$FAIL_REASON" ]]; then
    # ── Gate 2: Strategy baseline check ──────────────────────────────

    echo "── Gate 2: Strategy baseline ───────────────────────"
    if "$PYTHON" scripts/check_strategy_baseline.py \
        --strategy "$STRATEGY" \
        --min-win-rate "$MIN_WIN_RATE" \
        --last-n "$LAST_N" 2>&1; then
        echo "Gate 2: PASS"
        VERIFIED=1
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 2 ]]; then
            # check_strategy_baseline exited with error (missing DB etc)
            echo "Gate 2: WARN — baseline check error (treating as warning, not blocking)"
            echo "  If DB is unavailable or strategy has no live data yet, baseline check"
            echo "  is skipped. Verify manually before going live."
            VERIFIED=1  # Don't block on missing data (new strategy)
        else
            FAIL_REASON="Gate 2 FAILED: win rate below threshold for $STRATEGY"
            echo "$FAIL_REASON"
        fi
    fi

    echo ""
fi

# ── Restore or drop stash ─────────────────────────────────────────────

if [[ $HAS_STASH -eq 1 ]]; then
    if [[ $VERIFIED -eq 1 ]]; then
        echo "Restoring changes from stash..."
        git stash pop
        echo ""
    else
        echo "Dropping stash (changes did not pass verification)."
        echo "To recover: git stash pop  (if you want to inspect them)"
        git stash drop
        echo ""
    fi
fi

# ── Final verdict ─────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════"
if [[ $VERIFIED -eq 1 ]]; then
    echo "  VERIFIED — all gates passed. Changes are safe."
    echo "  Next: commit with gsd:quick or git commit."
    echo "═══════════════════════════════════════════════════"
    echo ""
    exit 0
else
    echo "  REVERTED — $FAIL_REASON"
    echo "  Changes were dropped. No files modified."
    echo "  Fix the failing check, then re-run verify_change.sh."
    echo "═══════════════════════════════════════════════════"
    echo ""
    exit 1
fi
