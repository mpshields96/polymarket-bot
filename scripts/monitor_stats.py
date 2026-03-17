import sqlite3, datetime, sys
conn = sqlite3.connect('/Users/matthewshields/Projects/polymarket-bot/data/polybot.db')
today = datetime.datetime(2026, 3, 17, 0, 0, 0, tzinfo=datetime.timezone.utc).timestamp()
r = conn.execute('SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), SUM(pnl_cents) FROM trades WHERE is_paper=0 AND created_at>=? AND result IS NOT NULL', (today,)).fetchone()
t, w, p = r[0] or 0, r[1] or 0, round((r[2] or 0)/100, 2)
a = conn.execute('SELECT SUM(pnl_cents) FROM trades WHERE is_paper=0 AND result IS NOT NULL').fetchone()
alltime = round((a[0] or 0)/100, 2)
wr = round(100*w/t) if t else 0
print(f"{t} settled | {w}W/{t-w}L ({wr}%) | {p} USD today | all-time={alltime} USD")
