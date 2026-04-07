# TODAY'S TASKS — April 6 2026 CST
# Visible to: ALL chats (Kalshi main, CCA, Codex, research)
# Last updated: S166 — full market discovery overhaul mandate

## ══════════════════════════════════════════════════════════════
## DIRECTIVE 1: CST TIMEZONE — ALL P&L TRACKING (Matthew, S166, PERMANENT)
## ══════════════════════════════════════════════════════════════
- "Today" = midnight CST (06:00 UTC) to midnight CST (06:00 UTC next day)
- "This month" = April 1 00:00 CST = 2026-04-01 06:00 UTC
- NEVER use UTC midnight as day boundary for daily P&L reports
- Query pattern:  midnight_cst_utc = datetime(Y, M, D, 6, 0, 0, tzinfo=timezone.utc)
- Today CST P&L: -2.51 USD | April CST: +59.32 USD | All-time: +129.21 USD

## ══════════════════════════════════════════════════════════════
## DIRECTIVE 2: SPORTS DAILY CAP — RAISE FROM 8 TO 30 (Matthew, S166, URGENT)
## ══════════════════════════════════════════════════════════════
- sports_game_loop max_daily_bets=8 is blocking bets after 8 are placed
- Tonight: bot placed 8 bets then hit cap — missed additional edge games
- FIX NEEDED: raise to 30 in main.py sports_game_loop call
- File: main.py, grep for "sports_game_loop(" to find call site
- Also: daily reset uses UTC midnight; should switch to CST midnight (06:00 UTC)

## ══════════════════════════════════════════════════════════════
## DIRECTIVE 3: FULL KALSHI MARKET DISCOVERY OVERHAUL (Matthew, S166, MAJOR)
## ══════════════════════════════════════════════════════════════

### CURRENT STATE (how market discovery works RIGHT NOW):
Every loop in the bot uses a HARDCODED series ticker. Examples:
  - sports_game_loop: hardcoded _SPORT_SERIES dict, 9 fixed series
  - daily_sniper_loop: hardcoded series_ticker="KXBTCD" or "KXETHD"
  - economics_sniper_loop: hardcoded KXCPI/KXGDP series
  - expiry_sniper: hardcoded KXBTC15M/KXETH15M/KXSOL15M

The sports_game_loop _SPORT_SERIES dict (main.py ~line 2123):
  "basketball_nba"           -> KXNBAGAME
  "icehockey_nhl"            -> KXNHLGAME
  "baseball_mlb"             -> KXMLBGAME
  "soccer_epl"               -> KXEPLGAME
  "soccer_uefa_champs_league"-> KXUCLGAME
  "soccer_germany_bundesliga"-> KXBUNDESLIGAGAME
  "soccer_italy_serie_a"     -> KXSERIEAGAME
  "soccer_spain_la_liga"     -> KXLALIGAGAME
  "soccer_france_ligue_one"  -> KXLIGUE1GAME

For each sport: get_markets(series_ticker=X, status="open") + match vs Odds API.
72h horizon window, 15-80c price range, min 5% edge, min 3 books.

### THE PROBLEM:
- Kalshi has 9,490 series and 30,000+ open markets
- Bot checks 9 hardcoded sports series only
- Missing: NFL, tennis, golf, college sports (KXNCAA*), 
  multi-event parlays (KXMVESPORTS, KXMVECROSSCATEGORY),
  politics (KXSENATE*, KXGOV*), entertainment, economics beyond CPI/GDP,
  and any NEW sports series Kalshi adds
- No mechanism to DISCOVER new series automatically
- Massive missed betting volume

### WHAT THE OVERHAUL NEEDS:
A new module: src/data/kalshi_series_discovery.py

  class KalshiSeriesDiscovery:
    async def get_all_series(self) -> List[SeriesInfo]
      # Paginate /series endpoint (9490 total) with volume filter
      
    async def get_all_open_markets(self, min_volume=100) -> Dict[str, List[Market]]
      # Returns {series_prefix: [markets]} for all non-crypto series with volume
      
    def classify_series(self, ticker: str, title: str) -> SeriesCategory
      # Maps series ticker to category: SPORTS / ECONOMICS / POLITICS / OTHER
      
    def get_odds_api_key(self, kalshi_series: str) -> Optional[str]
      # Maps known series to Odds API sport key:
      #   KXNFLGAME -> "americanfootball_nfl"
      #   KXNBAGAME -> "basketball_nba"
      #   KXNHLGAME -> "icehockey_nhl"
      #   KXMLBGAME -> "baseball_mlb"
      #   KXEPLGAME -> "soccer_epl"
      #   etc. (need full mapping)

The sports_game_loop should call this instead of its hardcoded dict:
  discovered = await discovery.get_all_open_markets()
  for series_prefix, markets in discovered.items():
    odds_key = discovery.get_odds_api_key(series_prefix)
    if odds_key:
      # compare vs Odds API consensus (existing logic)
    else:
      # log as uncovered — CCA research needed for signal

### KNOWN KALSHI SERIES (from S166 scan, volume > 5K):
  KXNBAGAME: 9.6M vol (NBA game winners — playoffs April 19+)
  KXNHLGAME: 1.25M vol (NHL game winners — playoffs April 19+)
  KXUCLGAME: 1.87M vol (UCL semis April 21+)
  KXMLBGAME: 47K vol (MLB daily games)
  KXEPLGAME: 124K vol (EPL)
  KXCPI: 1M+ vol (closes April 10)
  KXGDP: 512K vol (closes April 30)
  KXFED: 86K vol (long term)
  KXMVESPORTS: 13K vol (multi-event parlays)
  KXMVECROSSCATEGORY: 8.7K vol (cross-sport parlays)
  (more to discover — 9490 series total)

### ODDS API KEYS TO MAP (need CCA research):
  americanfootball_nfl    -> KXNFLGAME? (need to verify series exists)
  tennis (ATP/WTA)        -> KXTENNISGAME? (need to verify)
  golf                    -> KXGOLF? (need to verify)
  mma_mixed_martial_arts  -> KXUFCFIGHT (confirmed exists, opens ~2 weeks pre-event)
  soccer_mls              -> KXMLSGAME? (need to verify)
  baseball_ncaa           -> unknown Kalshi series
  basketball_ncaab        -> KXNCAABB* (confirmed exists in S166 series scan)

## ══════════════════════════════════════════════════════════════
## TASK LIST FOR ALL CHATS
## ══════════════════════════════════════════════════════════════

### KALSHI MAIN CHAT (S166 — immediate):
- [x] Raise sports_game_loop max_daily_bets from 8 to 30 in main.py
- [ ] Restart bot after cap change
- [ ] Verify sports_game fires more bets tonight
- [ ] Port efficiency_feed.py Phase 2 from agentic-rd-sandbox
- [ ] Economics sniper live decision for April 10 CPI (paper→live)

### CCA (urgent research):
- [ ] Build full Odds API sport key -> Kalshi series prefix mapping
      (What Kalshi series exist for NFL, tennis, golf, MMA, MLS, college?)
- [ ] Design KalshiSeriesDiscovery class (see spec above)
- [ ] Research NFL/MMA/tennis edges: do FLB patterns hold in these markets?
- [ ] CPI April 10 recommendation: which markets to target live? what prices?
- [ ] GDP April 30 recommendation: paper vs live? which thresholds?
- [ ] Multi-event parlay analysis: KXMVESPORTS 13K vol — edge mechanism?

### CODEX (urgent modeling):
- [ ] Model minimum-variance portfolio for 25 USD/day using:
      BTC daily sniper (5 USD/bet, 99.5% WR, ~15-20 bets/day)
      Sports game (2-5 USD/bet, expanding from 9 to 30+ series)
      Economics sniper (CPI: 5-10 USD/bet, April 10+)
      NBA/NHL playoffs (April 19+, 5 USD/bet)
- [ ] Simulate: what combination of bet caps + series coverage hits 25 USD/day with <15 USD std dev?
- [ ] Map which Odds API sport keys have Kalshi equivalents (systematic search)

## ══════════════════════════════════════════════════════════════
## CURRENT BOT STATE
## ══════════════════════════════════════════════════════════════
Bot: RUNNING PID=1656 -> /tmp/polybot_session166.log
Today CST (April 6): -2.51 USD (15 settled, 87% WR — ETH sniper -9.10 dominated)
April CST total: +59.32 USD (96 settled, 98% WR)
All-time: +129.21 USD | Bankroll: ~200 USD
Sports game bets placed today: 8+ (cap hit, additional bets blocked)
Games detected and bet on: April 6 (STL, PIT, MIL, MIA, CLE), April 7 (MIN), April 8 (PHI), April 9 (DET)
Daily cap status: BLOCKER — must raise before tomorrow's games
