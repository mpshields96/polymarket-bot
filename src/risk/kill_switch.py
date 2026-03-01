"""
Kill switch — all hard stops for polymarket-bot.

Every trade must pass check_order_allowed() before submission.
All checks are SYNCHRONOUS — no await here.

Triggers:
  SOFT (auto-reset):
    1. Single trade would exceed $5 OR 5% of bankroll (lower applies)
    2. Daily P&L loss > 15% of starting bankroll  → resets at midnight
    3. 4 consecutive losses → 2hr cooling period
    4. Hourly trade count > 15 → rate-limit pause

  HARD (manual reset required):
    5. 3+ consecutive auth failures
    6. Total bankroll loss > 30%
    7. Bankroll < $20
    8. kill_switch.lock file exists at startup

Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot (risk.py)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOCK_FILE = PROJECT_ROOT / "kill_switch.lock"
EVENT_LOG = PROJECT_ROOT / "KILL_SWITCH_EVENT.log"

# ── Hard limits — these cannot be changed by config ──────────────
HARD_MAX_TRADE_USD = 5.00         # Absolute ceiling per trade
HARD_STOP_LOSS_PCT = 0.30         # 30% total bankroll loss = hard stop
HARD_MIN_BANKROLL_USD = 20.00     # Below $20 = hard stop
DAILY_LOSS_LIMIT_PCT = 0.20       # 20% daily loss = soft kill (resets midnight)
CONSECUTIVE_LOSS_LIMIT = 4        # Losses before cooling period
COOLING_PERIOD_HOURS = 2          # Hours to pause after CONSECUTIVE_LOSS_LIMIT
MAX_HOURLY_TRADES = 15            # Trades per hour before rate-limit pause
MAX_AUTH_FAILURES = 3             # Consecutive auth failures before halt
MAX_TRADE_PCT = 0.05              # 5% of bankroll per trade


class KillSwitchState:
    """All mutable state for the kill switch. Persisted to disk on hard stops."""

    def __init__(self, starting_bankroll_usd: float):
        self.starting_bankroll = starting_bankroll_usd

        # Hard stop state
        self._hard_stop: bool = False
        self._hard_stop_reason: str = ""

        # Soft stop state
        self._soft_stop: bool = False
        self._soft_stop_reason: str = ""
        self._soft_stop_until: Optional[float] = None  # unix timestamp

        # Daily tracking (resets at midnight UTC)
        self._daily_date: str = self._today()
        self._daily_loss_usd: float = 0.0
        self._daily_trades: int = 0

        # Consecutive loss tracking
        self._consecutive_losses: int = 0
        self._cooling_until: Optional[float] = None

        # Hourly trade tracking
        self._hour_key: str = self._current_hour()
        self._hourly_trades: int = 0

        # Auth failure tracking
        self._consecutive_auth_failures: int = 0

        # Lifetime bankroll loss tracking
        self._realized_loss_usd: float = 0.0

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _current_hour(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")

    def _rotate_daily(self):
        today = self._today()
        if self._daily_date != today:
            logger.info("Daily rotation: %s → %s (daily loss was $%.2f)",
                        self._daily_date, today, self._daily_loss_usd)
            self._daily_date = today
            self._daily_loss_usd = 0.0
            self._daily_trades = 0
            # Auto-clear soft stops that were daily-loss-triggered
            if self._soft_stop and "daily loss" in self._soft_stop_reason.lower():
                logger.info("Soft kill auto-cleared on new trading day")
                self._soft_stop = False
                self._soft_stop_reason = ""
                self._soft_stop_until = None

    def _rotate_hourly(self):
        hour = self._current_hour()
        if self._hour_key != hour:
            self._hour_key = hour
            self._hourly_trades = 0

    def _check_cooling_expired(self):
        if self._cooling_until and time.time() > self._cooling_until:
            logger.info("Cooling period expired — consecutive loss counter reset")
            self._cooling_until = None
            self._consecutive_losses = 0
            if "consecutive" in self._soft_stop_reason.lower():
                self._soft_stop = False
                self._soft_stop_reason = ""


class KillSwitch:
    """
    Centralized kill switch. Call check_order_allowed() before every trade.
    All methods are synchronous.
    """

    def __init__(self, starting_bankroll_usd: float):
        self._state = KillSwitchState(starting_bankroll_usd)
        logger.info("KillSwitch initialized (starting bankroll: $%.2f)", starting_bankroll_usd)

    # ── Pre-trade gate ────────────────────────────────────────────

    def check_order_allowed(
        self,
        trade_usd: float,
        current_bankroll_usd: float,
        minutes_remaining: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Run all risk checks. Must be called BEFORE every trade.

        Returns:
            (True, "OK") if trade is allowed
            (False, reason) if blocked — log the reason always
        """
        state = self._state
        state._rotate_daily()
        state._rotate_hourly()
        state._check_cooling_expired()

        # ── Hard stops (never auto-reset) ────────────────────────
        if LOCK_FILE.exists():
            return False, "kill_switch.lock exists — run: python main.py --reset-killswitch"

        if state._hard_stop:
            return False, f"HARD STOP: {state._hard_stop_reason}"

        # ── Soft stops (may auto-reset) ──────────────────────────
        if state._soft_stop:
            if state._soft_stop_until and time.time() < state._soft_stop_until:
                remaining_min = (state._soft_stop_until - time.time()) / 60
                return False, f"SOFT STOP: {state._soft_stop_reason} ({remaining_min:.0f}min remaining)"
            elif not state._soft_stop_until:
                return False, f"SOFT STOP: {state._soft_stop_reason}"

        # ── Bankroll floor (checked before pct cap) ──────────────
        if current_bankroll_usd <= HARD_MIN_BANKROLL_USD:
            self._hard_stop(f"Bankroll ${current_bankroll_usd:.2f} at or below minimum ${HARD_MIN_BANKROLL_USD:.2f}")
            return False, state._hard_stop_reason

        # ── Per-trade size check ──────────────────────────────────
        if trade_usd > HARD_MAX_TRADE_USD:
            return False, f"Trade ${trade_usd:.2f} exceeds hard cap ${HARD_MAX_TRADE_USD:.2f}"

        pct_of_bankroll = trade_usd / current_bankroll_usd if current_bankroll_usd > 0 else 1.0
        if pct_of_bankroll > MAX_TRADE_PCT:
            return False, (
                f"Trade ${trade_usd:.2f} = {pct_of_bankroll:.1%} of bankroll "
                f"(max {MAX_TRADE_PCT:.0%})"
            )

        # ── Daily loss limit ──────────────────────────────────────
        daily_limit_usd = state.starting_bankroll * DAILY_LOSS_LIMIT_PCT
        if state._daily_loss_usd >= daily_limit_usd:
            reason = f"Daily loss ${state._daily_loss_usd:.2f} >= limit ${daily_limit_usd:.2f}"
            state._soft_stop = True
            state._soft_stop_reason = reason
            state._soft_stop_until = None  # resets at midnight
            return False, f"SOFT STOP: {reason}"

        # ── Consecutive loss cooling ──────────────────────────────
        if state._cooling_until and time.time() < state._cooling_until:
            remaining_min = (state._cooling_until - time.time()) / 60
            return False, f"Cooling period: {state._consecutive_losses} consecutive losses ({remaining_min:.0f}min remaining)"

        # ── Hourly rate limit ─────────────────────────────────────
        if state._hourly_trades >= MAX_HOURLY_TRADES:
            return False, f"Hourly rate limit: {state._hourly_trades} trades this hour (max {MAX_HOURLY_TRADES})"

        # ── Time remaining in market window ───────────────────────
        if minutes_remaining is not None and minutes_remaining <= 5:
            return False, f"Only {minutes_remaining:.1f}min remaining in market window (min 5)"

        return True, "OK"

    def check_paper_order_allowed(
        self,
        trade_usd: float,
        current_bankroll_usd: float,
    ) -> tuple[bool, str]:
        """
        Kill switch check for paper trades. Only hard stops block paper trades.

        Soft stops (daily loss, consecutive losses, hourly rate) do NOT block
        paper bets — paper data collection must continue during soft kills.
        Paper losses aren't real money; stopping paper during a soft kill wastes
        calibration data that's needed to evaluate strategy performance.

        Still blocks on:
          - kill_switch.lock (manual hard stop)
          - in-memory hard stop (30% bankroll loss, auth failures)
          - Bankroll below $20 floor (always hard stop regardless of paper/live)

        Does NOT block on:
          - Daily loss soft stop
          - Consecutive loss cooling period
          - Hourly rate limit
        """
        state = self._state
        state._rotate_daily()

        if LOCK_FILE.exists():
            return False, "kill_switch.lock exists — run: python main.py --reset-killswitch"

        if state._hard_stop:
            return False, f"HARD STOP: {state._hard_stop_reason}"

        if current_bankroll_usd <= HARD_MIN_BANKROLL_USD:
            self._hard_stop(
                f"Bankroll ${current_bankroll_usd:.2f} at or below minimum ${HARD_MIN_BANKROLL_USD:.2f}"
            )
            return False, state._hard_stop_reason

        return True, "OK"

    # ── Post-trade recording ──────────────────────────────────────

    def record_trade(self):
        """Call after every successful trade placement."""
        self._state._hourly_trades += 1
        self._state._daily_trades += 1

    def record_loss(self, loss_usd: float):
        """Call when a trade settles as a loss."""
        if loss_usd <= 0:
            return
        self._state._daily_loss_usd += loss_usd
        self._state._realized_loss_usd += loss_usd
        self._state._consecutive_losses += 1

        logger.warning("Loss recorded: $%.2f (consecutive: %d, daily total: $%.2f)",
                       loss_usd, self._state._consecutive_losses, self._state._daily_loss_usd)

        # Check consecutive loss limit
        if self._state._consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            until = time.time() + (COOLING_PERIOD_HOURS * 3600)
            self._state._cooling_until = until
            reason = f"{self._state._consecutive_losses} consecutive losses — cooling {COOLING_PERIOD_HOURS}hr"
            self._state._soft_stop = True
            self._state._soft_stop_reason = reason
            self._state._soft_stop_until = until
            logger.warning("COOLING PERIOD TRIGGERED: %s", reason)

        # Check total bankroll loss (hard stop)
        total_loss_pct = self._state._realized_loss_usd / self._state.starting_bankroll
        if total_loss_pct >= HARD_STOP_LOSS_PCT:
            self._hard_stop(
                f"Total bankroll loss {total_loss_pct:.1%} >= {HARD_STOP_LOSS_PCT:.0%} limit"
            )

    def restore_daily_loss(self, loss_usd: float):
        """Restore today's live loss total from the DB on bot restart.

        Prevents bot restarts from resetting the DAILY loss counter to 0 mid-session.
        Only touches _daily_loss_usd — NOT _realized_loss_usd (that is the lifetime
        hard stop counter and is restored separately via restore_realized_loss()).
        """
        if loss_usd <= 0:
            return
        self._state._daily_loss_usd += loss_usd
        logger.info(
            "Daily live loss restored from DB: $%.2f (today's running limit: $%.2f / $%.2f)",
            loss_usd,
            self._state._daily_loss_usd,
            self._state.starting_bankroll * DAILY_LOSS_LIMIT_PCT,
        )

    def restore_realized_loss(self, loss_usd: float):
        """Restore all-time live loss total from the DB on bot restart.

        Prevents the 30% lifetime hard stop from resetting to 0 on restart.
        Only touches _realized_loss_usd — NOT _daily_loss_usd (that is restored
        separately via restore_daily_loss()).

        Called on startup with db.all_time_live_loss_usd() so lifetime losses
        accumulate correctly across calendar days and session restarts.
        """
        if loss_usd <= 0:
            return
        self._state._realized_loss_usd = loss_usd  # set, not add — avoids double-count
        lifetime_pct = loss_usd / self._state.starting_bankroll
        logger.info(
            "Lifetime live loss restored from DB: $%.2f (%.1f%% of $%.2f hard stop at 30%%)",
            loss_usd,
            lifetime_pct * 100,
            self._state.starting_bankroll,
        )
        # If lifetime losses already exceed hard stop, trigger immediately
        if lifetime_pct >= HARD_STOP_LOSS_PCT:
            self._hard_stop(
                f"Lifetime loss ${loss_usd:.2f} ({lifetime_pct:.1%}) restored from DB "
                f">= {HARD_STOP_LOSS_PCT:.0%} hard stop limit"
            )

    def restore_consecutive_losses(self, count: int):
        """Restore consecutive live loss streak from the DB on bot restart.

        Prevents bot restarts from resetting the consecutive loss counter to 0
        mid-streak, which previously allowed the bot to place extra losing bets
        after already reaching the 4-loss cooling threshold.

        If count >= CONSECUTIVE_LOSS_LIMIT: triggers a fresh 2hr cooling period
        immediately so the bot cannot trade on restart after a breach.
        If count < limit: seeds the counter so fewer additional losses are needed
        to trigger cooling (e.g. restored at 3 → 1 more loss fires it).

        Called on startup with db.current_live_consecutive_losses().
        """
        if count <= 0:
            return
        self._state._consecutive_losses = count
        logger.info(
            "Consecutive live losses restored from DB: %d (limit: %d)",
            count,
            CONSECUTIVE_LOSS_LIMIT,
        )
        if count >= CONSECUTIVE_LOSS_LIMIT:
            until = time.time() + (COOLING_PERIOD_HOURS * 3600)
            self._state._cooling_until = until
            reason = (
                f"{count} consecutive losses restored from DB — "
                f"cooling {COOLING_PERIOD_HOURS}hr"
            )
            self._state._soft_stop = True
            self._state._soft_stop_reason = reason
            self._state._soft_stop_until = until
            logger.warning("COOLING PERIOD TRIGGERED ON RESTART: %s", reason)

    def record_win(self):
        """Call when a trade settles as a win."""
        self._state._consecutive_losses = 0
        logger.info("Win recorded — consecutive loss counter reset")

    def record_auth_failure(self):
        """Call on every API authentication failure."""
        self._state._consecutive_auth_failures += 1
        logger.warning("Auth failure #%d (max: %d)",
                       self._state._consecutive_auth_failures, MAX_AUTH_FAILURES)

        if self._state._consecutive_auth_failures >= MAX_AUTH_FAILURES:
            reason = f"{self._state._consecutive_auth_failures} consecutive auth failures"
            self._hard_stop(reason)
            self._write_blockers(reason)

    def record_auth_success(self):
        """Call on every successful API authentication."""
        if self._state._consecutive_auth_failures > 0:
            logger.info("Auth success — failure counter reset")
        self._state._consecutive_auth_failures = 0

    # ── Hard stop execution ───────────────────────────────────────

    def _hard_stop(self, reason: str):
        """Trigger a hard stop. Writes lock file and event log. Non-reversible without --reset-killswitch."""
        if self._state._hard_stop:
            return  # Already stopped

        self._state._hard_stop = True
        self._state._hard_stop_reason = reason
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.critical("🚨 HARD STOP TRIGGERED: %s", reason)

        # Skip file writes during tests — same guard as _write_blockers()
        # Prevents KILL_SWITCH_EVENT.log and kill_switch.lock from being polluted
        # by test-triggered hard stops (TestHardStopNoPollutionDuringTests)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return

        # Write lock file
        try:
            LOCK_FILE.write_text(json.dumps({
                "triggered_at": timestamp,
                "reason": reason,
                "starting_bankroll": self._state.starting_bankroll,
                "realized_loss_usd": self._state._realized_loss_usd,
            }, indent=2))
        except Exception as e:
            logger.error("Failed to write kill_switch.lock: %s", e)

        # Write event log
        try:
            with open(EVENT_LOG, "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"HARD STOP — {timestamp}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Starting bankroll: ${self._state.starting_bankroll:.2f}\n")
                f.write(f"Total loss: ${self._state._realized_loss_usd:.2f}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            logger.error("Failed to write KILL_SWITCH_EVENT.log: %s", e)

        # Print instructions
        print("\n" + "=" * 60)
        print("🚨  HARD STOP TRIGGERED")
        print(f"    Reason: {reason}")
        print(f"    Time:   {timestamp}")
        print()
        print("    Trading has been halted. All new orders will be blocked.")
        print("    To resume after reviewing:")
        print()
        print("    python main.py --reset-killswitch")
        print()
        print("    Review KILL_SWITCH_EVENT.log before resetting.")
        print("=" * 60 + "\n")

    def _write_blockers(self, reason: str):
        """Write to BLOCKERS.md when auth failures halt the bot. Skipped during tests."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return  # Don't pollute BLOCKERS.md with expected test-triggered auth failures
        blockers_path = PROJECT_ROOT / "BLOCKERS.md"
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with open(blockers_path, "a") as f:
                f.write(f"\n## BLOCKER: Auth failure halt — {timestamp}\n")
                f.write(f"Severity: CRITICAL\n")
                f.write(f"Need: Kalshi auth failing — {reason}\n")
                f.write(f"Check: Is kalshi_private_key.pem correct? Is KALSHI_API_KEY_ID correct?\n")
                f.write(f"Fix: Verify keys match in Kalshi dashboard, re-download .pem if needed.\n")
                f.write(f"Status: OPEN\n")
        except Exception as e:
            logger.error("Failed to write BLOCKERS.md: %s", e)

    # ── Status ───────────────────────────────────────────────────

    @property
    def is_hard_stopped(self) -> bool:
        return self._state._hard_stop or LOCK_FILE.exists()

    @property
    def is_soft_stopped(self) -> bool:
        return self._state._soft_stop

    @property
    def hard_stop_reason(self) -> str:
        return self._state._hard_stop_reason

    @property
    def soft_stop_reason(self) -> str:
        return self._state._soft_stop_reason

    def get_status(self) -> dict:
        s = self._state
        s._rotate_daily()
        s._rotate_hourly()
        return {
            "hard_stop": self.is_hard_stopped,
            "hard_stop_reason": s._hard_stop_reason,
            "soft_stop": self.is_soft_stopped,
            "soft_stop_reason": s._soft_stop_reason,
            "daily_loss_usd": s._daily_loss_usd,
            "daily_loss_limit_usd": s.starting_bankroll * DAILY_LOSS_LIMIT_PCT,
            "daily_trades": s._daily_trades,
            "hourly_trades": s._hourly_trades,
            "consecutive_losses": s._consecutive_losses,
            "consecutive_auth_failures": s._consecutive_auth_failures,
            "total_realized_loss_usd": s._realized_loss_usd,
        }


# ── Startup lock file check ───────────────────────────────────────

def check_lock_at_startup() -> None:
    """
    Call at bot startup. Raises if kill_switch.lock exists.
    This is the gate that prevents a hard-stopped bot from restarting.
    """
    if LOCK_FILE.exists():
        try:
            data = json.loads(LOCK_FILE.read_text())
            reason = data.get("reason", "unknown")
            triggered_at = data.get("triggered_at", "unknown")
        except Exception:
            reason = "unknown (lock file unreadable)"
            triggered_at = "unknown"

        raise RuntimeError(
            f"\n{'='*60}\n"
            f"🚨  HARD STOP IS ACTIVE — Bot cannot start.\n\n"
            f"    Triggered: {triggered_at}\n"
            f"    Reason:    {reason}\n\n"
            f"    Review KILL_SWITCH_EVENT.log before resetting.\n"
            f"    To reset: python main.py --reset-killswitch\n"
            f"{'='*60}"
        )


def reset_kill_switch() -> None:
    """
    Called by: python main.py --reset-killswitch
    Removes kill_switch.lock after human review.
    """
    if not LOCK_FILE.exists():
        print("No kill_switch.lock found — nothing to reset.")
        return

    print("\n" + "=" * 60)
    print("KILL SWITCH RESET")
    print()

    try:
        data = json.loads(LOCK_FILE.read_text())
        print(f"  Triggered: {data.get('triggered_at', 'unknown')}")
        print(f"  Reason:    {data.get('reason', 'unknown')}")
        print(f"  Total loss recorded: ${data.get('realized_loss_usd', 0):.2f}")
    except Exception:
        print("  (Could not read lock file details)")

    print()
    print("  Before proceeding, ensure you understand why the stop triggered.")
    confirm = input("  Type 'RESET' to confirm: ").strip()
    if confirm != "RESET":
        print("  Reset cancelled.")
        return

    LOCK_FILE.unlink()
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(EVENT_LOG, "a") as f:
        f.write(f"\nRESET by human — {timestamp}\n")

    print("  ✅ Kill switch reset. Review your bankroll before trading.")
    print("  Run: python main.py --verify")
    print("=" * 60 + "\n")
