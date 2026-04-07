# Standing Directives — Kalshi Bot (permanent, all sessions)

## Autonomy
- Bypass permissions ACTIVE — run commands without confirmation
- Never ask for confirmation on: tests, reads, edits, commits, restarts, reports, research
- Do work first, summarize after
- Matthew is a doctor with a new baby — no time for back-and-forth

## Budget & Model
- Model: Opus 4.6
- Budget: 30% of session token limit MAX per chat (two parallel chats may run)
- Peak hours (8AM-2PM ET weekdays): 40-50% of normal budget
- Off-peak (all other times): 100% budget

## Live Bets Priority
- Live bot health = top priority above all else
- If bot dies: restart IMMEDIATELY before anything else
- Never change strategy parameters without explicit Matthew approval
- Never disable live strategies
- Never commit anything that could break the bot

## Strategy Bans (permanent)
- 15-min crypto markets BANNED from live: KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M
  (btc_lag, eth_lag, sol_lag, btc_drift, eth_drift, sol_drift, btc_imbalance, eth_imbalance,
  expiry_sniper, maker_sniper — ALL banned regardless of edge data)
- Paper accumulation OK. NEVER re-enable live even if SPRT/CUSUM looks good. Ban is structural.

## DAILY PROFIT TRACKING — CST ONLY (Matthew directive, S166 — PERMANENT)
- ALL daily P&L tracking uses Central Standard Time (CST = UTC-6). No UTC. No CDT.
- "Today" = midnight CST to midnight CST (= 06:00 UTC to 06:00 UTC next day)
- "This month" = April 1 00:00 CST = 2026-04-01 06:00 UTC onward
- Query pattern:
    from datetime import datetime, timezone, timedelta
    cst_midnight_utc = datetime(Y, M, D, 6, 0, 0, tzinfo=timezone.utc)  # midnight CST
    april_start_utc = datetime(2026, 4, 1, 6, 0, 0, tzinfo=timezone.utc)
- NEVER report "today" using UTC midnight as the boundary. Always use CST (06:00 UTC boundary).
- Applies to: ALL chats — Kalshi main, research, CCA cross-chat reports. PERMANENT.

## Session tip
Output one loading screen tip at the end of every response (one recommendation).
