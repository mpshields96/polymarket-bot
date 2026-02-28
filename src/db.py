"""
SQLite persistence layer.

JOB:    Store and retrieve trades, P&L, bankroll snapshots, kill switch events.
        Schema created automatically on first run.

DOES NOT: Business logic. Just read/write. No decisions here.

Uses standard library sqlite3 (synchronous). Writes are fast (<5ms) for
SQLite local files — acceptable to call from async context without await.

Tables:
    trades              — every trade (paper + live)
    daily_pnl           — one summary row per trading day
    bankroll_history    — periodic balance snapshots
    kill_switch_events  — log of every kill switch trigger
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_DB_PATH = PROJECT_ROOT / "kalshi_bot.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL NOT NULL,
    ticker          TEXT NOT NULL,
    side            TEXT NOT NULL,          -- 'yes' | 'no'
    action          TEXT NOT NULL,          -- 'buy' | 'sell'
    price_cents     INTEGER NOT NULL,       -- limit price in cents (1-99)
    count           INTEGER NOT NULL,       -- number of contracts
    cost_usd        REAL NOT NULL,          -- dollars spent (price_cents/100 * count)
    strategy        TEXT DEFAULT 'btc_lag',
    edge_pct        REAL,
    win_prob        REAL,
    is_paper        INTEGER NOT NULL DEFAULT 1,  -- 1=paper, 0=live
    client_order_id TEXT,
    server_order_id TEXT,
    result          TEXT,                   -- 'yes' | 'no' | NULL (unsettled)
    pnl_cents       INTEGER,                -- P&L in cents after settlement
    settled_at      REAL,
    created_at      REAL DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_ticker   ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_ts       ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_is_paper ON trades(is_paper);

CREATE TABLE IF NOT EXISTS daily_pnl (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL UNIQUE,   -- 'YYYY-MM-DD'
    starting_bankroll   REAL,
    realized_pnl_usd    REAL DEFAULT 0.0,
    fees_usd            REAL DEFAULT 0.0,
    num_trades          INTEGER DEFAULT 0,
    num_wins            INTEGER DEFAULT 0,
    is_paper            INTEGER DEFAULT 1,
    created_at          REAL DEFAULT (strftime('%s','now')),
    updated_at          REAL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS bankroll_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL NOT NULL,
    balance_usd REAL NOT NULL,
    source      TEXT DEFAULT 'api',    -- 'api' | 'paper_simulation'
    created_at  REAL DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_bankroll_ts ON bankroll_history(timestamp);

CREATE TABLE IF NOT EXISTS kill_switch_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           REAL NOT NULL,
    trigger_type        TEXT NOT NULL,  -- 'hard_stop' | 'soft_stop' | 'reset'
    reason              TEXT NOT NULL,
    bankroll_at_trigger REAL,
    created_at          REAL DEFAULT (strftime('%s','now'))
);
"""


class DB:
    """
    Synchronous SQLite wrapper.

    Open once at startup, reuse throughout the session. Thread-safe if
    opened with check_same_thread=False.
    """

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def init(self):
        """Open the database and create tables if they don't exist."""
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        logger.info("DB initialized at %s", self._db_path)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *_):
        self.close()

    # ── Trades ────────────────────────────────────────────────────────

    def save_trade(
        self,
        ticker: str,
        side: str,
        action: str,
        price_cents: int,
        count: int,
        cost_usd: float,
        *,
        strategy: str = "btc_lag",
        edge_pct: Optional[float] = None,
        win_prob: Optional[float] = None,
        is_paper: bool = True,
        client_order_id: Optional[str] = None,
        server_order_id: Optional[str] = None,
    ) -> int:
        """Insert a new trade record. Returns the new row ID."""
        cursor = self._conn.execute(
            """INSERT INTO trades
               (timestamp, ticker, side, action, price_cents, count, cost_usd,
                strategy, edge_pct, win_prob, is_paper, client_order_id, server_order_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                time.time(), ticker, side, action, price_cents, count, cost_usd,
                strategy, edge_pct, win_prob, int(is_paper),
                client_order_id, server_order_id,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid

    def settle_trade(
        self,
        trade_id: int,
        result: str,         # "yes" | "no"
        pnl_cents: int,      # net P&L in cents (after fees)
    ):
        """Record settlement outcome on a trade."""
        self._conn.execute(
            """UPDATE trades
               SET result = ?, pnl_cents = ?, settled_at = ?
               WHERE id = ?""",
            (result, pnl_cents, time.time(), trade_id),
        )
        self._conn.commit()

    def get_trades(
        self,
        is_paper: Optional[bool] = None,
        ticker: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent trades, newest first."""
        query = "SELECT * FROM trades WHERE 1=1"
        params: list = []
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_open_trades(self, is_paper: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Return unsettled trades."""
        query = "SELECT * FROM trades WHERE result IS NULL"
        params: list = []
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ── Daily P&L ─────────────────────────────────────────────────────

    def upsert_daily_pnl(
        self,
        date: str,
        realized_pnl_usd: float,
        fees_usd: float,
        num_trades: int,
        num_wins: int,
        starting_bankroll: Optional[float] = None,
        is_paper: bool = True,
    ):
        """Insert or update the P&L row for today."""
        existing = self._conn.execute(
            "SELECT id FROM daily_pnl WHERE date = ?", (date,)
        ).fetchone()

        if existing:
            self._conn.execute(
                """UPDATE daily_pnl
                   SET realized_pnl_usd = ?, fees_usd = ?, num_trades = ?,
                       num_wins = ?, updated_at = ?
                   WHERE date = ?""",
                (realized_pnl_usd, fees_usd, num_trades, num_wins, time.time(), date),
            )
        else:
            self._conn.execute(
                """INSERT INTO daily_pnl
                   (date, starting_bankroll, realized_pnl_usd, fees_usd, num_trades, num_wins, is_paper)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (date, starting_bankroll, realized_pnl_usd, fees_usd, num_trades, num_wins, int(is_paper)),
            )
        self._conn.commit()

    def get_daily_pnl(self, limit: int = 30) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM daily_pnl ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Bankroll history ──────────────────────────────────────────────

    def save_bankroll(self, balance_usd: float, source: str = "api"):
        self._conn.execute(
            "INSERT INTO bankroll_history (timestamp, balance_usd, source) VALUES (?, ?, ?)",
            (time.time(), balance_usd, source),
        )
        self._conn.commit()

    def latest_bankroll(self) -> Optional[float]:
        """Return the most recent recorded balance, or None."""
        row = self._conn.execute(
            "SELECT balance_usd FROM bankroll_history ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return row["balance_usd"] if row else None

    def get_bankroll_history(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM bankroll_history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Kill switch events ────────────────────────────────────────────

    def save_kill_switch_event(
        self,
        trigger_type: str,
        reason: str,
        bankroll_at_trigger: Optional[float] = None,
    ):
        self._conn.execute(
            """INSERT INTO kill_switch_events
               (timestamp, trigger_type, reason, bankroll_at_trigger)
               VALUES (?, ?, ?, ?)""",
            (time.time(), trigger_type, reason, bankroll_at_trigger),
        )
        self._conn.commit()

    def get_kill_switch_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM kill_switch_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats ─────────────────────────────────────────────────────────

    def count_trades_today(self, strategy: str, is_paper: Optional[bool] = None) -> int:
        """Return number of bets placed today for a given strategy (UTC day)."""
        from datetime import datetime, timezone as _tz
        now_utc = datetime.now(_tz.utc)
        midnight_utc = now_utc.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()
        query = "SELECT COUNT(*) FROM trades WHERE strategy = ? AND timestamp >= ?"
        params: list = [strategy, midnight_utc]
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        row = self._conn.execute(query, params).fetchone()
        return row[0] or 0

    def has_open_position(self, ticker: str, is_paper: Optional[bool] = None) -> bool:
        """Return True if there is an unsettled trade on this exact ticker."""
        query = "SELECT COUNT(*) FROM trades WHERE ticker = ? AND result IS NULL"
        params: list = [ticker]
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        row = self._conn.execute(query, params).fetchone()
        return (row[0] or 0) > 0

    def win_rate(self, is_paper: Optional[bool] = None, limit: int = 100) -> Optional[float]:
        """Return win rate (0.0–1.0) over last `limit` settled trades, or None."""
        query = "SELECT result, side FROM trades WHERE result IS NOT NULL"
        params: list = []
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        query += " ORDER BY settled_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        if not rows:
            return None
        wins = sum(1 for r in rows if dict(r)["result"] == dict(r)["side"])
        return wins / len(rows)

    def total_realized_pnl_usd(self, is_paper: Optional[bool] = None) -> float:
        """Return sum of all settled P&L in USD."""
        query = "SELECT SUM(pnl_cents) FROM trades WHERE result IS NOT NULL"
        params: list = []
        if is_paper is not None:
            query += " AND is_paper = ?"
            params.append(int(is_paper))
        row = self._conn.execute(query, params).fetchone()
        total_cents = row[0] or 0
        return total_cents / 100.0


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> DB:
    """Build DB from config.yaml, or use default path."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return DB()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    db_path_str = cfg.get("storage", {}).get("db_path", "kalshi_bot.db")
    db_path = Path(db_path_str)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return DB(db_path)
