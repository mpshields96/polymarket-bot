"""
Streamlit dashboard — read-only monitoring UI.

JOB:    Display bot status, P&L, trades, and system health at localhost:8501.
        Optimized for narrow side-panel layout (~460px wide).
        Auto-refreshes every 5 minutes.

DOES NOT: Business logic, API calls, risk decisions, order placement.

Run with:
    streamlit run src/dashboard.py --server.port 8501 --server.headless true --server.fileWatcherType none

Data source: kalshi_bot.db (SQLite) — reads only, never writes.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).parent.parent
LOCK_FILE = PROJECT_ROOT / "kill_switch.lock"
PID_FILE = PROJECT_ROOT / "bot.pid"

# Kill switch constants — must match src/risk/kill_switch.py
DAILY_LOSS_LIMIT_USD = 20.0
CONSECUTIVE_LOSS_LIMIT = 4


def _resolve_db_path() -> Path:
    try:
        import yaml
        config_path = PROJECT_ROOT / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            db_path_str = cfg.get("storage", {}).get("db_path", "kalshi_bot.db")
            db_path = Path(db_path_str)
            if not db_path.is_absolute():
                db_path = PROJECT_ROOT / db_path
            return db_path
    except Exception:
        pass
    return PROJECT_ROOT / "kalshi_bot.db"


DB_PATH = _resolve_db_path()

st.set_page_config(
    page_title="POLYBOT",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject CSS to tighten up spacing for narrow panel
st.markdown("""
<style>
    /* Tighten global padding */
    .block-container { padding: 0.5rem 0.8rem 1rem 0.8rem !important; max-width: 100% !important; }
    /* Shrink metric labels and values */
    [data-testid="stMetricLabel"] { font-size: 0.70rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.65rem !important; }
    /* Tighten dataframe rows */
    .stDataFrame { font-size: 0.72rem !important; }
    /* Tighten subheaders */
    h2, h3 { font-size: 0.9rem !important; margin-bottom: 0.2rem !important; margin-top: 0.4rem !important; }
    /* Compact divider */
    hr { margin: 0.3rem 0 !important; }
    /* Progress text */
    .stProgress > div > div { font-size: 0.65rem !important; }
    /* Hide hamburger menu */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Auto-refresh every 5 minutes (300,000ms)
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
    st_autorefresh(interval=300_000, key="autorefresh")
except ImportError:
    pass


# ── Data loading ──────────────────────────────────────────────────────

@st.cache_resource
def get_db():
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


# ── Status helpers ────────────────────────────────────────────────────

def kill_switch_status() -> tuple[bool, str]:
    if LOCK_FILE.exists():
        try:
            import json
            data = json.loads(LOCK_FILE.read_text())
            return True, data.get("reason", "Unknown")
        except Exception:
            return True, "Lock file exists"
    return False, ""


def bot_is_alive() -> tuple[bool, int]:
    if not PID_FILE.exists():
        return False, 0
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True, pid
    except (ValueError, ProcessLookupError):
        return False, 0
    except PermissionError:
        return True, 0


def soft_stop_status(today: str) -> dict:
    daily_loss_cents = scalar(
        """SELECT SUM(ABS(pnl_cents)) FROM trades
           WHERE is_paper=0 AND result IS NOT NULL AND pnl_cents<0
             AND date(timestamp,'unixepoch')=?""",
        (today,), default=0,
    ) or 0
    live_results = query(
        """SELECT result, side FROM trades
           WHERE is_paper=0 AND result IS NOT NULL
           ORDER BY timestamp DESC LIMIT 20"""
    )
    streak = 0
    for row in live_results:
        if row["result"] != row["side"]:
            streak += 1
        else:
            break
    daily_loss_usd = daily_loss_cents / 100.0
    return {
        "daily_loss_usd": daily_loss_usd,
        "consecutive": streak,
        "soft_stopped": daily_loss_usd >= DAILY_LOSS_LIMIT_USD or streak >= CONSECUTIVE_LOSS_LIMIT,
    }


def _read_env_live() -> bool:
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


# ── Main ──────────────────────────────────────────────────────────────

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")

    is_live = (PROJECT_ROOT / ".env").exists() and _read_env_live()
    alive, pid = bot_is_alive()
    hard_stopped, stop_reason = kill_switch_status()
    soft = soft_stop_status(today)

    # ── Compact header ────────────────────────────────────────────────
    mode_color = "#ff4444" if is_live else "#4CAF50"
    mode_label = "🔴 LIVE" if is_live else "📋 PAPER"
    bot_dot = "🟢" if alive else "🔴"

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:2px'>"
        f"<span style='color:{mode_color};font-size:1.3rem;font-weight:700'>POLYBOT {mode_label}</span>"
        f"<span style='font-size:0.75rem;color:#888'>{bot_dot} PID {pid} · {now_str}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Status banner (one line) ──────────────────────────────────────
    if hard_stopped:
        st.error(f"🚨 HARD STOP — {stop_reason[:60]}")
    elif soft["soft_stopped"]:
        parts = []
        if soft["daily_loss_usd"] >= DAILY_LOSS_LIMIT_USD:
            parts.append(f"Daily loss ${soft['daily_loss_usd']:.2f}≥${DAILY_LOSS_LIMIT_USD:.0f}")
        if soft["consecutive"] >= CONSECUTIVE_LOSS_LIMIT:
            parts.append(f"{soft['consecutive']} consec losses")
        st.warning(f"⚠️ SOFT STOP — {' | '.join(parts)} — resets midnight UTC")
    else:
        st.success("✅ Operational — kill switch clear")

    if not DB_PATH.exists():
        st.warning("No DB found.")
        return

    st.divider()

    # ── Row 1: 3 key metrics ──────────────────────────────────────────
    bankroll = scalar(
        "SELECT balance_usd FROM bankroll_history ORDER BY timestamp DESC LIMIT 1",
        default=0.0,
    )
    today_live_pnl = (scalar(
        """SELECT SUM(pnl_cents) FROM trades
           WHERE result IS NOT NULL AND is_paper=0
             AND date(timestamp,'unixepoch')=?""",
        (today,), default=0,
    ) or 0) / 100.0
    alltime_live_pnl = (scalar(
        "SELECT SUM(pnl_cents) FROM trades WHERE result IS NOT NULL AND is_paper=0",
        default=0,
    ) or 0) / 100.0

    m1, m2, m3 = st.columns(3)
    m1.metric("Bankroll", f"${bankroll:.2f}")
    m2.metric("Today Live", f"${today_live_pnl:+.2f}")
    m3.metric("All-time Live", f"${alltime_live_pnl:+.2f}")

    # ── Row 2: win rate + open count ──────────────────────────────────
    live_settled = scalar(
        "SELECT COUNT(*) FROM trades WHERE result IS NOT NULL AND is_paper=0", default=0
    ) or 0
    live_wins = scalar(
        "SELECT COUNT(*) FROM trades WHERE result IS NOT NULL AND is_paper=0 AND result=side",
        default=0,
    ) or 0
    open_n = scalar("SELECT COUNT(*) FROM trades WHERE result IS NULL", default=0) or 0
    alltime_paper_pnl = (scalar(
        "SELECT SUM(pnl_cents) FROM trades WHERE result IS NOT NULL AND is_paper=1",
        default=0,
    ) or 0) / 100.0

    m4, m5, m6 = st.columns(3)
    wr = f"{live_wins/max(1,live_settled):.0%} ({live_wins}/{live_settled})" if live_settled else "—"
    m4.metric("Live Win Rate", wr)
    m5.metric("Open Positions", open_n)
    m6.metric("Paper P&L", f"${alltime_paper_pnl:+.2f}")

    st.divider()

    # ── Kill switch gauges (horizontal, compact) ──────────────────────
    st.markdown("**Kill Switch**")
    g1, g2 = st.columns(2)
    with g1:
        d_pct = min(1.0, soft["daily_loss_usd"] / DAILY_LOSS_LIMIT_USD)
        st.caption(f"Daily loss ${soft['daily_loss_usd']:.2f}/${DAILY_LOSS_LIMIT_USD:.0f}")
        st.progress(d_pct)
    with g2:
        c_pct = min(1.0, soft["consecutive"] / CONSECUTIVE_LOSS_LIMIT)
        st.caption(f"Streak {soft['consecutive']}/{CONSECUTIVE_LOSS_LIMIT}")
        st.progress(c_pct)

    st.divider()

    # ── Open positions (compact) ──────────────────────────────────────
    st.markdown("**Open Positions**")
    open_trades = query(
        """SELECT ticker, side, price_cents, cost_usd, is_paper, strategy, timestamp
           FROM trades WHERE result IS NULL ORDER BY timestamp DESC"""
    )
    if not open_trades:
        st.caption("None")
    else:
        rows = []
        for t in open_trades:
            ts = datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%H:%M") if t["timestamp"] else "—"
            rows.append({
                "T": ts,
                "Strat": (t["strategy"] or "—").replace("_v1", ""),
                "Side": t["side"].upper(),
                "¢": t["price_cents"],
                "$": f"${t['cost_usd']:.2f}",
                "M": "P" if t["is_paper"] else "L",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True, height=min(160, 40 + len(rows) * 35))

    st.divider()

    # ── Strategy P&L (compact) ────────────────────────────────────────
    st.markdown("**Strategy P&L (live only)**")
    strat_rows = query(
        """SELECT strategy,
               COUNT(CASE WHEN result IS NOT NULL THEN 1 END) AS settled,
               COUNT(CASE WHEN result IS NOT NULL AND result=side THEN 1 END) AS wins,
               SUM(CASE WHEN result IS NOT NULL THEN pnl_cents ELSE 0 END) AS pnl
           FROM trades WHERE is_paper=0
           GROUP BY strategy ORDER BY pnl DESC"""
    )
    if strat_rows:
        display = []
        for r in strat_rows:
            s = r["settled"] or 0
            w = r["wins"] or 0
            display.append({
                "Strategy": (r["strategy"] or "?").replace("_v1", ""),
                "W/L": f"{w}/{s-w}",
                "P&L": f"${(r['pnl'] or 0)/100:+.2f}",
            })
        st.dataframe(display, use_container_width=True, hide_index=True, height=min(200, 40 + len(display) * 35))

    st.divider()

    # ── Last 10 trades ────────────────────────────────────────────────
    st.markdown("**Last 10 Trades**")
    trades = query(
        """SELECT ticker, side, price_cents, cost_usd, result, pnl_cents,
                  is_paper, strategy, timestamp
           FROM trades ORDER BY timestamp DESC LIMIT 10"""
    )
    if not trades:
        st.caption("No trades yet.")
    else:
        rows = []
        for t in trades:
            ts = datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%H:%M") if t["timestamp"] else "—"
            result = t.get("result")
            pnl = t.get("pnl_cents")
            won = result is not None and result == t["side"]
            rows.append({
                "T": ts,
                "Strat": (t.get("strategy") or "—").replace("_v1", ""),
                "Side": t["side"].upper(),
                "¢": t["price_cents"],
                "P&L": f"${pnl/100:+.2f}" if pnl is not None else "—",
                "": ("✅" if won else "❌") if result else "⏳",
                "M": "P" if t["is_paper"] else "L",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True, height=min(380, 40 + len(rows) * 35))


if __name__ == "__main__":
    main()
