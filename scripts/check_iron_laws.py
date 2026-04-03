#!/usr/bin/env python3
"""
check_iron_laws.py — Verify BOUNDS.md line references against actual source files.

Reports CURRENT / STALE / MISSING for each Iron Law with a file:line reference.
Exit code 1 if any STALE or MISSING (safe to wire into pre-commit hook).

Usage:
    python scripts/check_iron_laws.py
    python scripts/check_iron_laws.py --verbose
"""

import sys
import os
import argparse

# ── Iron Law registry ─────────────────────────────────────────────────────────
# Each entry: (law_id, relative_file_path, stated_line, expected_keyword, description)
# expected_keyword: substring that must appear within ±5 lines of stated_line
IRON_LAWS = [
    ("IL-1a",  "src/execution/live.py",   127, "LIVE_TRADING",           "LIVE_TRADING env var gate"),
    ("IL-1b",  "src/execution/live.py",   135, "live_confirmed",         "live_confirmed CLI flag gate"),
    ("IL-3",   "src/risk/kill_switch.py",  39, "HARD_MAX_TRADE_USD",     "Hard max trade USD constant"),
    ("IL-4",   "src/strategies/expiry_sniper.py", 62, "_DEFAULT_TRIGGER_PRICE_CENTS", "Sniper trigger threshold 90c floor"),
    ("IL-5",   "src/execution/live.py",   168, "price_cents >= 99",      "Fee-floor guard 1c/99c block"),
    ("IL-6a",  "src/auth/kalshi_auth.py",  64, "key_path.name",          "No credential value logging"),
    ("IL-6b",  "src/auth/kalshi_auth.py", 111, "load_from_env",          "Env var validation function"),
    ("IL-7",   "src/execution/live.py",   641, "canceled",               "Canceled orders not recorded"),
    ("IL-8",   "src/execution/live.py",   660, "is_paper=False",         "Live executor always is_paper=False"),
    ("IL-9",   "src/risk/sizing.py",      157, "math.floor",             "Kelly floor truncation"),
    ("IL-12",  "src/risk/kill_switch.py", 176, "pct_of_bankroll",        "Kill switch pct-of-bankroll cap"),
    ("IL-14",  "main.py",                1982, "record_win",             "Settlement loop live-only accounting"),
    ("IL-16",  "src/execution/live.py",    36, "_FIRST_RUN_CONFIRMED",   "First-run flag initialization"),
    ("IL-17a", "src/risk/kill_switch.py", 168, "HARD_MIN_BANKROLL_USD",  "Bankroll floor check first"),
    ("IL-17b", "src/risk/kill_switch.py", 173, "HARD_MAX_TRADE_USD",     "Per-trade hard cap check second"),
    ("IL-17c", "src/risk/kill_switch.py", 176, "pct_of_bankroll",        "Pct-of-bankroll cap check third"),
]

WINDOW = 5  # ±lines to search around stated line number


def check_law(repo_root: str, law_id: str, rel_path: str, stated_line: int,
              keyword: str, description: str, verbose: bool) -> str:
    """
    Returns 'CURRENT', 'STALE', or 'MISSING'.
    CURRENT  — keyword found within ±WINDOW lines of stated_line
    STALE    — file exists but keyword not near stated_line
    MISSING  — file doesn't exist OR keyword not found anywhere in file
    """
    abs_path = os.path.join(repo_root, rel_path)

    if not os.path.isfile(abs_path):
        if verbose:
            print(f"  [{law_id}] MISSING — file not found: {rel_path}")
        return "MISSING"

    with open(abs_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total = len(lines)
    lo = max(0, stated_line - 1 - WINDOW)        # convert to 0-indexed
    hi = min(total, stated_line - 1 + WINDOW + 1)
    window_text = "".join(lines[lo:hi])

    if keyword in window_text:
        if verbose:
            found_at = next(
                (lo + i + 1 for i, l in enumerate(lines[lo:hi]) if keyword in l),
                stated_line,
            )
            print(f"  [{law_id}] CURRENT  — '{keyword}' near line {stated_line} (found ~{found_at})")
        return "CURRENT"

    # keyword not in window — check if it exists at all in the file
    full_text = "".join(lines)
    if keyword not in full_text:
        if verbose:
            print(f"  [{law_id}] MISSING  — '{keyword}' not found anywhere in {rel_path}")
        return "MISSING"

    # keyword exists elsewhere — line number is stale
    actual_lines = [i + 1 for i, l in enumerate(lines) if keyword in l]
    if verbose:
        print(f"  [{law_id}] STALE    — '{keyword}' stated line {stated_line}, "
              f"actually at {actual_lines} in {rel_path}")
    return "STALE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify BOUNDS.md Iron Law line references")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-law detail")
    args = parser.parse_args()

    # Repo root = directory containing this script's parent (scripts/../)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    results = {}
    for (law_id, rel_path, stated_line, keyword, description) in IRON_LAWS:
        status = check_law(repo_root, law_id, rel_path, stated_line,
                           keyword, description, args.verbose)
        results[law_id] = (status, rel_path, stated_line, keyword, description)

    # ── Summary ───────────────────────────────────────────────────────────────
    current = [k for k, v in results.items() if v[0] == "CURRENT"]
    stale   = [k for k, v in results.items() if v[0] == "STALE"]
    missing = [k for k, v in results.items() if v[0] == "MISSING"]

    print(f"\nIron Law Line Reference Check — {len(IRON_LAWS)} laws")
    print(f"  CURRENT : {len(current)}")
    print(f"  STALE   : {len(stale)}")
    print(f"  MISSING : {len(missing)}")

    if stale:
        print("\nSTALE (update BOUNDS.md line numbers):")
        for k in stale:
            _, rel_path, stated_line, keyword, description = results[k]
            print(f"  {k}: {description} — '{keyword}' stated line {stated_line} in {rel_path}")

    if missing:
        print("\nMISSING (file gone or keyword removed):")
        for k in missing:
            _, rel_path, stated_line, keyword, description = results[k]
            print(f"  {k}: {description} — '{keyword}' in {rel_path}:{stated_line}")

    if not stale and not missing:
        print("\nAll Iron Law references CURRENT. BOUNDS.md is accurate.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
