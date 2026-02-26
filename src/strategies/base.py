"""
Strategy base class and Signal dataclass.

JOB:    Defines the interface all strategies must implement.
        Every strategy returns a Signal or None from generate_signal().

DOES NOT: Know about sizing, risk, order placement, or API calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.platforms.kalshi import Market, OrderBook
    from src.data.binance import BinanceFeed


@dataclass
class Signal:
    """
    Trading signal output by a strategy.

    All fields are required. Sizing module uses win_prob, edge_pct, and price_cents.
    """
    side: str           # "yes" | "no" — which side to buy
    edge_pct: float     # estimated edge after fees (e.g. 0.10 = 10%). Always > 0.
    win_prob: float     # estimated P(win) in [0, 1]
    confidence: float   # subjective confidence in [0, 1] (0 = minimum, 1 = maximum)
    ticker: str         # Kalshi market ticker
    price_cents: int    # current limit price for our side (1-99)
    reason: str = field(default="")  # human-readable explanation for logs

    def __post_init__(self):
        if self.side not in ("yes", "no"):
            raise ValueError(f"Signal.side must be 'yes' or 'no', got {self.side!r}")
        if not (0 < self.edge_pct < 1):
            raise ValueError(f"Signal.edge_pct must be in (0, 1), got {self.edge_pct}")
        if not (0 <= self.win_prob <= 1):
            raise ValueError(f"Signal.win_prob must be in [0, 1], got {self.win_prob}")
        if not (1 <= self.price_cents <= 99):
            raise ValueError(f"Signal.price_cents must be 1–99, got {self.price_cents}")


class BaseStrategy(ABC):
    """
    Abstract base for all trading strategies.

    Subclasses implement generate_signal() and return a Signal (trade this)
    or None (no opportunity right now).

    Design rule: no await inside generate_signal(). All async work (fetching
    market data, orderbook) is done by the caller before calling this method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier, used in logs and DB records."""
        ...

    @abstractmethod
    def generate_signal(
        self,
        market: "Market",
        orderbook: "OrderBook",
        btc_feed: "BinanceFeed",
    ) -> Optional[Signal]:
        """
        Evaluate current market state and return a Signal or None.

        This method is SYNCHRONOUS. All I/O must be done before calling this.

        Args:
            market:    Current Kalshi market snapshot (yes_price, no_price, close_time, ...)
            orderbook: Current Kalshi order book (yes_bids, no_bids)
            btc_feed:  Live Binance feed (call btc_move_pct(), current_price())

        Returns:
            Signal if there's a trade opportunity, None to hold.
        """
        ...
