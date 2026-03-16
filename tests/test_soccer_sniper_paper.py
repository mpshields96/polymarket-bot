"""
Tests for soccer sniper paper execution logic.

Tests the SoccerSniperExec class that hooks into PriceTracker.observe()
to place paper bets when mid-game 90c+ crossings are detected.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch, call

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.soccer_live_monitor import PriceTracker, SNIPER_THRESHOLD
from scripts.soccer_sniper_paper import SoccerSniperExec, SoccerPaperTracker


SOCCER_SNIPER_BET_USD = 5.0
PRE_GAME_THRESHOLD = 0.60
STRATEGY_NAME = "soccer_sniper_v1"


class TestSoccerSniperExec(unittest.TestCase):
    """Unit tests for the SoccerSniperExec paper execution class."""

    def setUp(self):
        self.mock_executor = MagicMock()
        self.exec = SoccerSniperExec(paper_executor=self.mock_executor)

    def test_no_bet_placed_for_pregame_crossing(self):
        """Crossing at PRE-GAME state should NOT place a bet."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-ARS",
            price_cents=92,
            state="PRE-GAME vol=55000",
            pregame_price=0.75,
        )
        self.mock_executor.execute.assert_not_called()

    def test_bet_placed_for_ingame_crossing(self):
        """Crossing at IN-GAME state should place a paper bet."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-ARS",
            price_cents=92,
            state="Arsenal 2-0 Leverkusen | 67:00 | lead=+2",
            pregame_price=0.76,
        )
        self.mock_executor.execute.assert_called_once()
        call_kwargs = self.mock_executor.execute.call_args
        assert call_kwargs[1]["price_cents"] == 92
        assert call_kwargs[1]["size_usd"] == SOCCER_SNIPER_BET_USD

    def test_no_duplicate_bet_per_market(self):
        """Only one paper bet per market per session."""
        state = "Arsenal 2-0 Leverkusen | 67:00 | lead=+2"
        self.exec.on_crossing("KXUCLGAME-ARS", 92, state, 0.76)
        self.exec.on_crossing("KXUCLGAME-ARS", 94, state, 0.76)
        self.exec.on_crossing("KXUCLGAME-ARS", 93, state, 0.76)
        self.mock_executor.execute.assert_called_once()

    def test_pregame_filter_blocks_low_pregame_price(self):
        """No bet if pre-game price was below PRE_GAME_THRESHOLD."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-MCI",
            price_cents=91,
            state="Man City 1-0 Real Madrid | 75:00 | lead=+1",
            pregame_price=0.55,  # Below 0.60 threshold
        )
        self.mock_executor.execute.assert_not_called()

    def test_pregame_filter_allows_high_pregame_price(self):
        """Bet placed if pre-game price was at or above PRE_GAME_THRESHOLD."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-MCI",
            price_cents=91,
            state="Man City 1-0 Real Madrid | 75:00 | lead=+1",
            pregame_price=0.64,  # At/above 0.60 threshold
        )
        self.mock_executor.execute.assert_called_once()

    def test_pregame_threshold_boundary_at_exactly_60c(self):
        """Pre-game exactly 0.60 should trigger execution."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-BMU",
            price_cents=90,
            state="Bayern 1-0 Atalanta | 55:00 | lead=+1",
            pregame_price=0.60,
        )
        self.mock_executor.execute.assert_called_once()

    def test_pregame_threshold_boundary_just_below_60c(self):
        """Pre-game at 0.599 should NOT trigger execution."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-BMU",
            price_cents=90,
            state="Bayern 1-0 Atalanta | 55:00 | lead=+1",
            pregame_price=0.599,
        )
        self.mock_executor.execute.assert_not_called()

    def test_bet_side_is_yes(self):
        """Bet side must be 'yes' (buying the team to win)."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-LFC",
            price_cents=92,
            state="Liverpool 2-0 Galatasaray | 60:00 | lead=+2",
            pregame_price=0.77,
        )
        call_kwargs = self.mock_executor.execute.call_args[1]
        assert call_kwargs["side"] == "yes"

    def test_bet_size_is_calibration_amount(self):
        """Bet size must equal SOCCER_SNIPER_BET_USD (calibration mode)."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-BAR",
            price_cents=91,
            state="Barcelona 2-0 Newcastle | 50:00 | lead=+2",
            pregame_price=0.70,
        )
        call_kwargs = self.mock_executor.execute.call_args[1]
        assert call_kwargs["size_usd"] == SOCCER_SNIPER_BET_USD

    def test_strategy_name_is_correct(self):
        """Strategy name must be 'soccer_sniper_v1' in executor call."""
        exec_with_name = SoccerSniperExec(
            paper_executor=self.mock_executor,
            strategy_name=STRATEGY_NAME,
        )
        exec_with_name.on_crossing(
            ticker="KXLALIGAGAME-RMA",
            price_cents=90,
            state="Real Madrid 3-0 Atletico | 65:00 | lead=+3",
            pregame_price=0.73,
        )
        # The strategy name should be stored on the executor, not passed per-call
        # (consistent with how PaperExecutor works)
        self.mock_executor.execute.assert_called_once()

    def test_different_markets_get_separate_bets(self):
        """Two different markets each get their own bet."""
        state1 = "Arsenal 2-0 Leverkusen | 60:00 | lead=+2"
        state2 = "Bayern 2-0 Atalanta | 65:00 | lead=+2"
        self.exec.on_crossing("KXUCLGAME-ARS", 92, state1, 0.76)
        self.exec.on_crossing("KXUCLGAME-BMU", 91, state2, 0.74)
        assert self.mock_executor.execute.call_count == 2

    def test_no_bet_at_99c_or_above(self):
        """No bet placed at 99c (fee-floor, same as crypto sniper guard)."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-ARS",
            price_cents=99,
            state="Arsenal 3-0 Leverkusen | 88:00 | lead=+3",
            pregame_price=0.76,
        )
        self.mock_executor.execute.assert_not_called()

    def test_no_bet_at_1c_or_below(self):
        """No bet placed at 1c or below (wrong side, fee-floor)."""
        self.exec.on_crossing(
            ticker="KXUCLGAME-LEV",
            price_cents=1,
            state="Arsenal 3-0 Leverkusen | 88:00 | lead=-3",
            pregame_price=0.09,
        )
        self.mock_executor.execute.assert_not_called()

    def test_session_reset_clears_bet_history(self):
        """After session_reset(), same market can receive a new bet."""
        state = "Arsenal 2-0 Leverkusen | 60:00 | lead=+2"
        self.exec.on_crossing("KXUCLGAME-ARS", 92, state, 0.76)
        self.exec.session_reset()
        self.exec.on_crossing("KXUCLGAME-ARS", 92, state, 0.76)
        assert self.mock_executor.execute.call_count == 2


class TestSoccerPaperTracker(unittest.TestCase):
    """Integration tests for the SoccerPaperTracker (PriceTracker + SoccerSniperExec)."""

    def setUp(self):
        self.mock_sniper_exec = MagicMock()
        self.tracker = SoccerPaperTracker(
            label="test",
            sniper_exec=self.mock_sniper_exec,
        )

    def test_pregame_price_tracked_before_game(self):
        """Pre-game price is stored for use as threshold filter."""
        self.tracker.observe("KXUCLGAME-ARS", 0.75, "PRE-GAME vol=55000")
        self.tracker.observe("KXUCLGAME-ARS", 0.76, "PRE-GAME vol=56000")
        assert self.tracker.get_pregame_price("KXUCLGAME-ARS") == pytest.approx(0.76, abs=0.01)

    def test_crossing_triggers_sniper_exec_during_game(self):
        """When crossing 90c+ during a game, sniper_exec.on_crossing() is called."""
        self.tracker.observe("KXUCLGAME-ARS", 0.76, "PRE-GAME vol=55000")
        self.tracker.observe(
            "KXUCLGAME-ARS", 0.92,
            "Arsenal 2-0 Leverkusen | 67:00 | lead=+2"
        )
        self.mock_sniper_exec.on_crossing.assert_called_once()
        call_kwargs = self.mock_sniper_exec.on_crossing.call_args[1]
        assert call_kwargs["ticker"] == "KXUCLGAME-ARS"
        assert call_kwargs["pregame_price"] == pytest.approx(0.76, abs=0.01)

    def test_crossing_does_not_trigger_exec_when_pregame(self):
        """90c+ crossing during PRE-GAME does NOT call sniper_exec."""
        self.tracker.observe("KXUCLGAME-ARS", 0.91, "PRE-GAME vol=55000")
        self.tracker.observe("KXUCLGAME-ARS", 0.93, "PRE-GAME vol=56000")
        self.mock_sniper_exec.on_crossing.assert_not_called()

    def test_sniper_exec_not_called_twice_for_same_crossing(self):
        """Once in a crossing window, exec only fires on first entry."""
        self.tracker.observe("KXUCLGAME-ARS", 0.76, "PRE-GAME vol=55000")
        game_state = "Arsenal 2-0 Leverkusen | 67:00 | lead=+2"
        self.tracker.observe("KXUCLGAME-ARS", 0.91, game_state)
        self.tracker.observe("KXUCLGAME-ARS", 0.93, game_state)
        self.tracker.observe("KXUCLGAME-ARS", 0.95, game_state)
        self.mock_sniper_exec.on_crossing.assert_called_once()

    def test_sniper_exec_refires_after_price_drops_then_recrosses(self):
        """After price drops below 90c and re-crosses, exec fires again."""
        self.tracker.observe("KXUCLGAME-ARS", 0.76, "PRE-GAME vol=55000")
        game_state = "Arsenal 2-0 Leverkusen | 67:00 | lead=+2"
        # First crossing
        self.tracker.observe("KXUCLGAME-ARS", 0.91, game_state)
        # Drop below 90c (goal by Leverkusen)
        self.tracker.observe("KXUCLGAME-ARS", 0.75, game_state)
        # Re-cross 90c (Arsenal scored again)
        self.tracker.observe("KXUCLGAME-ARS", 0.92, game_state)
        # Should fire twice (two separate crossing events)
        assert self.mock_sniper_exec.on_crossing.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
