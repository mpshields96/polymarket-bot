"""
Streamlit dashboard — read-only monitoring UI.

JOB:    Display bot status, P&L, trades, and system health at localhost:8501.
        Auto-refreshes every 30 seconds.

DOES NOT: Business logic, API calls, risk decisions, order placement.

Run with:
    streamlit run src/dashboard.py

Data source: kalshi_bot.db (SQLite) — reads only, never writes.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "kalshi_bot.db"
LOCK_FILE = PROJECT_ROOT / "kill_switch.lock"
EVENT_LOG = PROJECT_ROOT / "KILL_SWITCH_EVENT.log"

st.set_page_config(
    page_title="POLYBOT",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 30 seconds
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
    st_autorefresh(interval=30_000, key="autorefresh")
except ImportError:
    pass  # streamlit-autorefresh is optional


# ── Data loading ──────────────────────────────────────────────────────

@st.cache_resource
def get_db():
    """Get DB connection (cached resource — one connection per session)."""
    import sqlite3
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def scalar(sql: str, params: tuple = (), default=None):
    conn = get_db()
    if conn is None:
        return default
    try:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception:
        return default


# ── Kill switch status ────────────────────────────────────────────────

def kill_switch_status() -> tuple[bool, str]:
    """Return (is_hard_stopped, reason)."""
    if LOCK_FILE.exists():
        try:
            import json
            data = json.loads(LOCK_FILE.read_text())
            return True, data.get("reason", "Unknown")
        except Exception:
            return True, "Lock file exists (unreadable)"
    return False, ""


# ── Main dashboard ────────────────────────────────────────────────────

def main():
    # ── Kill switch banner ────────────────────────────────────────────
    hard_stopped, stop_reason = kill_switch_status()

    if hard_stopped:
        st.error(f"🚨 HARD STOP ACTIVE — {stop_reason}")
        st.error("Run: `python main.py --reset-killswitch` to resume after review.")
    else:
        st.success("✅ Kill switch clear — bot is operational")

    # ── Mode + header ─────────────────────────────────────────────────
    is_live = (PROJECT_ROOT / ".env").exists() and _read_env_live()
    mode_label = "🔴 LIVE" if is_live else "📋 PAPER"
    mode_color = "#ff4444" if is_live else "#4CAF50"

    st.markdown(
        f"<h1 style='color:{mode_color}; margin-bottom:0'>POLYBOT — {mode_label}</h1>",
        unsafe_allow_html=True,
    )
    st.caption(f"Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} · DB: {DB_PATH.name}")

    if not DB_PATH.exists():
        st.warning("No database found. Run `python main.py` first to start the bot.")
        return

    st.divider()

    # ── Row 1: key metrics ────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    # Bankroll
    bankroll = scalar(
        "SELECT balance_usd FROM bankroll_history ORDER BY timestamp DESC LIMIT 1",
        default=0.0,
    )
    col1.metric("Bankroll", f"${bankroll:.2f}")

    # Today's P&L
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_pnl_cents = scalar(
        "SELECT SUM(pnl_cents) FROM trades WHERE result IS NOT NULL AND date(timestamp,'unixepoch') = ?",
        (today,), default=0,
    ) or 0
    today_pnl = today_pnl_cents / 100.0
    col2.metric("Today's P&L", f"${today_pnl:+.2f}", delta=f"${today_pnl:+.2f}")

    # All-time P&L
    alltime_pnl_cents = scalar(
        "SELECT SUM(pnl_cents) FROM trades WHERE result IS NOT NULL",
        default=0,
    ) or 0
    col3.metric("All-time P&L", f"${alltime_pnl_cents/100:+.2f}")

    # Win rate
    total_settled = scalar("SELECT COUNT(*) FROM trades WHERE result IS NOT NULL", default=0) or 0
    wins = scalar(
        "SELECT COUNT(*) FROM trades WHERE result IS NOT NULL AND result = side",
        default=0,
    ) or 0
    win_rate = f"{wins/max(1,total_settled):.0%}" if total_settled > 0 else "—"
    col4.metric("Win Rate", win_rate, help=f"{wins}/{total_settled} settled trades")

    st.divider()

    # ── Row 2: today's activity ───────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Today")
        today_trades = query(
            "SELECT COUNT(*) as n FROM trades WHERE date(timestamp,'unixepoch') = ?",
            (today,),
        )
        today_n = today_trades[0]["n"] if today_trades else 0
        open_n = scalar(
            "SELECT COUNT(*) FROM trades WHERE result IS NULL AND date(timestamp,'unixepoch') = ?",
            (today,), default=0,
        ) or 0
        today_wins = scalar(
            "SELECT COUNT(*) FROM trades WHERE result IS NOT NULL AND result = side AND date(timestamp,'unixepoch') = ?",
            (today,), default=0,
        ) or 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Trades", today_n)
        c2.metric("Open", open_n)
        c3.metric("Wins", today_wins)

    with col_b:
        st.subheader("System Health")
        # Kill switch events
        ks_events = scalar("SELECT COUNT(*) FROM kill_switch_events", default=0) or 0
        # DB size
        db_size_mb = DB_PATH.stat().st_size / 1_048_576 if DB_PATH.exists() else 0
        # Last bankroll update
        last_update_ts = scalar(
            "SELECT timestamp FROM bankroll_history ORDER BY timestamp DESC LIMIT 1",
            default=None,
        )
        if last_update_ts:
            age_min = (time.time() - last_update_ts) / 60
            last_update_str = f"{age_min:.0f}min ago"
        else:
            last_update_str = "Never"

        h1, h2, h3 = st.columns(3)
        h1.metric("Kill events", ks_events)
        h2.metric("DB size", f"{db_size_mb:.1f} MB")
        h3.metric("Last update", last_update_str)

    st.divider()

    # ── Last 10 trades ────────────────────────────────────────────────
    st.subheader("Last 10 Trades")

    trades = query(
        """SELECT ticker, side, action, price_cents, count, cost_usd,
                  result, pnl_cents, is_paper, strategy, timestamp
           FROM trades
           ORDER BY timestamp DESC
           LIMIT 10"""
    )

    if not trades:
        st.info("No trades yet.")
    else:
        rows = []
        for t in trades:
            ts = datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%m-%d %H:%M") if t["timestamp"] else "—"
            result = t.get("result")
            pnl = t.get("pnl_cents")
            pnl_str = f"${pnl/100:+.2f}" if pnl is not None else "open"
            won = result is not None and result == t["side"]
            rows.append({
                "Time": ts,
                "Ticker": t["ticker"],
                "Side": t["side"].upper(),
                "Price": f"{t['price_cents']}¢",
                "Qty": t["count"],
                "Cost": f"${t['cost_usd']:.2f}",
                "Result": ("✅ WIN" if won else "❌ LOSS") if result else "⏳ open",
                "P&L": pnl_str,
                "Mode": "PAPER" if t["is_paper"] else "LIVE",
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()

    # ── Kill switch log ───────────────────────────────────────────────
    st.subheader("Kill Switch Events")
    ks_rows = query(
        "SELECT timestamp, trigger_type, reason FROM kill_switch_events ORDER BY timestamp DESC LIMIT 10"
    )
    if not ks_rows:
        st.info("No kill switch events recorded.")
    else:
        display = []
        for r in ks_rows:
            ts = datetime.fromtimestamp(r["timestamp"], timezone.utc).strftime("%m-%d %H:%M UTC")
            display.append({
                "Time": ts,
                "Type": r["trigger_type"],
                "Reason": r["reason"],
            })
        st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Tips ──────────────────────────────────────────────────────────
    st.divider()
    with st.expander("Tips"):
        st.markdown("""
**Paper mode:** Bot is running in simulation. No real money at risk.

**Going live:**
1. Set `LIVE_TRADING=true` in `.env`
2. Run `python main.py --live`
3. Type `CONFIRM` at the prompt

**If kill switch triggers:**
```bash
cat KILL_SWITCH_EVENT.log   # review what happened
python main.py --reset-killswitch
```

**Check P&L from terminal:**
```bash
python main.py --report
```
        """)


def _read_env_live() -> bool:
    """Read LIVE_TRADING from .env file directly (not os.environ)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return False
    try:
        for line in env_path.read_text().splitlines():
            if line.strip().startswith("LIVE_TRADING"):
                _, _, val = line.partition("=")
                return val.strip().lower() == "true"
    except Exception:
        pass
    return False


if __name__ == "__main__":
    main()
