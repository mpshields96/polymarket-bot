---
paths:
  - ~/Projects/titanium-experimental/**
  - ~/Projects/titanium-v36/**
---

# Titanium Field Name Invariants

These field names are locked across both repos. Do not create aliases or alternate versions.

## BetCandidate fields (edge_calculator.py)

| Correct name | Do NOT use |
|---|---|
| `std_dev` | `consensus_std_dev`, `book_std_dev`, `price_std_dev` |
| `sharp_score` | `score`, `sharp` |
| `sharp_breakdown` | `breakdown`, `score_breakdown` |
| `kill_reason` | `kill_msg`, `kill_flag` |
| `edge_pct` | `edge`, `edge_percent` |
| `win_prob` | `prob`, `win_probability` |
| `fair_implied` | `fair_prob`, `vig_free_prob` |
| `market_implied` | `implied_prob`, `market_prob` |

## v36-confirmed: std_dev
- v36 shipped F2 (std_dev WARNING badge) in v36 Session 16
- The BetCandidate field is named `std_dev`
- R&D validation script uses `consensus_std_dev` as a local variable only — do NOT promote that name to any dataclass field
- If you see `consensus_std_dev` referenced as a dataclass field anywhere, rename it to `std_dev`

## Kill switch return type
- All kill switches return `(bool, str)` — NOT `Optional[str]`, NOT `tuple[bool, Optional[str]]`
- Changed in Session 6. Do not revert.
- `killed=True` → drop candidate. `killed=False, reason!=""` → FLAG, keep candidate.

## Quota constant names (locked — must match between v36 + sandbox)
Both repos must use these exact names. Do not create synonyms.

| Constant | Value | Do NOT use |
|---|---|---|
| `DAILY_CREDIT_CAP` | 1000 | `DAILY_LIMIT`, `DAILY_HARD_CAP`, `MAX_DAILY` |
| `SESSION_CREDIT_HARD_STOP` | 500 | `SESSION_CAP`, `SESSION_LIMIT`, `HARD_STOP` |
| `SESSION_CREDIT_SOFT_LIMIT` | 300 | `SOFT_LIMIT`, `WARN_LIMIT` |
| `BILLING_RESERVE` | 1000 | `MIN_REMAINING`, `FLOOR`, `RESERVE` |

## Quota class names (locked)
| Correct name | Do NOT use |
|---|---|
| `DailyCreditLog` | `DailyLog`, `CreditLog`, `DailyCounter` |
| `QuotaTracker` | `QuotaManager`, `ApiQuota`, `CreditsTracker` |

File: `daily_quota.json` — always at project root (v36) or `data/daily_quota.json` (sandbox core/ level).
Never commit `daily_quota.json` — it is runtime state, always gitignored.
