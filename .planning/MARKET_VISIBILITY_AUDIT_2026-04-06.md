# Market Visibility Audit Note — April 6 2026

Purpose: align the planning stack with the code that already exists, then define the next blocker clearly.

## What The Live Sports Loop Already Does

Observed in `main.py`:

- Filters bookmaker games to roughly the next `24 hours`, not `72 hours`
- Sorts Kalshi sports markets by parsed ticker date so earlier games are evaluated first
- Skips Kalshi sports markets that appear already in-game (`start_time < now - 5 min`)
- Keeps per-sport live caps and paper-only overrides

This means the remaining problem is not "add another basic time guard." The remaining problem is visibility and auditability.

## Existing Discovery / Audit Tooling

The repo already has usable scanners:

- `scripts/audit_all_kalshi_markets.py`
  - Pulls all open markets with pagination
  - Pulls all series and events
  - Produces broad category / volume breakdowns
- `scripts/kalshi_series_scout.py`
  - Weekly scout for uncovered high-volume series
  - Best for ranked expansion candidates
- `scripts/edge_scanner.py`
  - Compares covered sports series against bookmaker odds
  - Useful for "covered sports board seen vs matched" checks

## The Actual Gap

We still do not have one authoritative report that answers all of these at once:

1. Which open Kalshi markets exist right now across the full exchange?
2. Which series are visible to the live bot today?
3. Which same-day sports boards are visible vs skipped?
4. How many sports markets are same-day vs days-out?
5. Which uncovered high-volume non-sports series should be researched next?

That is why the bot can still feel blind even though some discovery scripts already exist.

## Next Engineering Target

Before new strategy variants or new sports lanes:

1. Build a single visibility report that combines:
   - full open-market audit
   - same-day vs days-out sports counts
   - covered-vs-uncovered series status
2. Make same-day sports visibility a required precondition in session init / wrap.
3. Treat new sports or non-sports expansions as downstream of this audit, not a substitute for it.

## Practical Conclusion

The next session should prioritize a unified market-visibility report, not more sniper ideation and not another pass on already-landed sports date guards.
