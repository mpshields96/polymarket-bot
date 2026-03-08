---
phase: quick
plan: 5
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/probe_polymarket_orders.py
  - .planning/research/copy_trading_research.md
autonomous: true
requirements: [COPYTRADE-ORDER-SCHEMA]
must_haves:
  truths:
    - "We know whether POST /v1/orders on polymarket.us accepts JSON or another format"
    - "We know what fields the order body requires (or the error message that tells us)"
    - "We know whether the /portfolio/activities response reveals past order field names"
    - "copy_trading_research.md has a concrete ORDER SCHEMA section with findings"
  artifacts:
    - path: "scripts/probe_polymarket_orders.py"
      provides: "Safe, non-trading probe script that reads error responses and existing data"
    - path: ".planning/research/copy_trading_research.md"
      provides: "Updated with POST /v1/orders schema findings"
  key_links:
    - from: "scripts/probe_polymarket_orders.py"
      to: "src/auth/polymarket_auth.py"
      via: "load_from_env() + PolymarketAuth.headers()"
      pattern: "load_from_env"
    - from: ".planning/research/copy_trading_research.md"
      to: "scripts/probe_polymarket_orders.py"
      via: "findings documented from script output"
---

<objective>
Discover the POST /v1/orders body schema on polymarket.us by sending safe probe requests
and reading the error responses, then documenting findings in copy_trading_research.md.

Purpose: POST /v1/orders format is the single remaining unknown blocking live copy trading
on polymarket.us. We cannot write a live executor without knowing the schema. The fastest
way to learn it is to ask the API itself — a deliberately minimal request will return a
validation error that names the required fields.

Output:
- scripts/probe_polymarket_orders.py — one-shot script, runs and exits, no loops
- copy_trading_research.md — updated with ORDER SCHEMA section
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
@/Users/matthewshields/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/research/copy_trading_research.md
@src/auth/polymarket_auth.py
@src/platforms/polymarket.py

<interfaces>
<!-- Key types the executor needs — no codebase exploration required. -->

From src/auth/polymarket_auth.py:
```python
class PolymarketAuth:
    def headers(self, method: str, path: str) -> dict[str, str]:
        """Returns X-PM-Access-Key, X-PM-Timestamp, X-PM-Signature, Content-Type."""

def load_from_env() -> PolymarketAuth:
    """Load from POLYMARKET_KEY_ID + POLYMARKET_SECRET_KEY in .env"""
```

From src/platforms/polymarket.py:
```python
_BASE_URL = "https://api.polymarket.us"
_API_PREFIX = "/v1"
# Price scale: 0.0–1.0 (NOT cents like Kalshi)
# Confirmed endpoints including POST /v1/orders (format TBD)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write and run probe script</name>
  <files>scripts/probe_polymarket_orders.py</files>
  <action>
Create scripts/probe_polymarket_orders.py that probes POST /v1/orders safely. The script
MUST NOT place a real order. It sends a minimal/malformed body and reads the error response,
which will reveal the required fields and format. Strategy:

1. Load auth via load_from_env() from src/auth/polymarket_auth.py. Import dotenv and load
   .env first (same pattern as other scripts in this repo).

2. Run three probes in sequence, print full response for each:

   PROBE A — Empty body POST:
   POST https://api.polymarket.us/v1/orders
   Body: {}
   Purpose: Get "required fields: X, Y, Z" validation error.

   PROBE B — Minimal plausible JSON body:
   POST https://api.polymarket.us/v1/orders
   Body: {"marketId": "probe-test", "side": "YES", "price": 0.5, "size": 1}
   Purpose: Confirm JSON is accepted (vs protobuf) and get field-name errors.

   PROBE C — GET /portfolio/activities (existing method):
   Call client.get_activities(limit=5) and print raw dicts.
   Purpose: Activities response likely shows past order shapes — field names visible.

3. For each probe, print:
   - HTTP status code
   - Full response body (text, NOT parsed JSON — even if it's an error)
   - Any Content-Type header from the response

4. Use requests (synchronous) for probes A+B since this is a one-shot script.
   Use asyncio.run() + aiohttp for probe C (reuses existing PolymarketClient).

5. Script ends with: print("=== PROBE COMPLETE ===")

IMPORTANT constraints:
- This script MUST NOT execute a real order. Any error response is expected and desired.
- Never log .env credentials. Print only status codes and response bodies.
- Script is single-use, put in scripts/ folder (not src/).
- Run the script after writing: `source venv/bin/activate && python scripts/probe_polymarket_orders.py`
- Capture the full output — it is the primary deliverable.
  </action>
  <verify>
    <automated>source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python /Users/matthewshields/Projects/polymarket-bot/scripts/probe_polymarket_orders.py 2>&1 | tail -30</automated>
  </verify>
  <done>
Script runs without crash. Three probe results printed with HTTP status codes and response
bodies. "=== PROBE COMPLETE ===" appears at the end. No real orders placed.
  </done>
</task>

<task type="auto">
  <name>Task 2: Document schema findings in copy_trading_research.md</name>
  <files>.planning/research/copy_trading_research.md</files>
  <action>
After running the probe script and capturing its output, append a new section to
.planning/research/copy_trading_research.md immediately after the existing KALSHI section
and before the TOP TRADERS section.

Section title: `## POST /v1/orders SCHEMA — CONFIRMED FINDINGS`
Section format:

```
══════════════════════════════════════════════════════════════
## POST /v1/orders SCHEMA — CONFIRMED FINDINGS
## Probed: {date}
══════════════════════════════════════════════════════════════

### Body format
[JSON | protobuf | unknown — based on probe A+B response]

### Required fields (from error responses)
[List each field name, type, and allowed values as revealed by error messages]
Example:
- marketId: string — the market identifier
- side: "YES" | "NO"
- price: float 0.0–1.0
- size: float (number of shares)
- orderType: "FOK" | "IOC" | "GTC" (if revealed)

### Error responses observed
Probe A (empty body): HTTP {status} — {body snippet}
Probe B (minimal JSON): HTTP {status} — {body snippet}

### Activities endpoint order shape
[Field names visible in /portfolio/activities response for trade-type activities]

### Implementation implication
[Single sentence: "We can now implement PolymarketClient.post_order() with these fields" OR
"Format is protobuf — requires protobuf schema discovery next" OR
"Field names confirmed — next step is live executor in src/execution/"]
```

Fill in all sections with ACTUAL data from the probe output. Do not leave placeholders.

After appending the section, verify the file reads back correctly.
  </action>
  <verify>
    <automated>grep -c "POST /v1/orders SCHEMA" /Users/matthewshields/Projects/polymarket-bot/.planning/research/copy_trading_research.md</automated>
  </verify>
  <done>
copy_trading_research.md contains a completed "POST /v1/orders SCHEMA — CONFIRMED FINDINGS"
section with actual probe results (no placeholders). The implementation implication sentence
is concrete — tells exactly what the next step is.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:
1. scripts/probe_polymarket_orders.py exists and runs clean
2. copy_trading_research.md has the new ORDER SCHEMA section with real findings
3. No real order was placed (confirmed by checking portfolio activities — balance unchanged)
4. The implementation implication in the research doc is actionable (names next step)
</verification>

<success_criteria>
- POST /v1/orders body format is known (JSON vs protobuf, required fields documented)
- copy_trading_research.md is updated with concrete findings
- Next action for live copy trading is unambiguous from the research doc
</success_criteria>

<output>
After completion, create `.planning/quick/5-probe-post-v1-orders-format-on-polymarke/5-SUMMARY.md`
with: what was found, what the order schema looks like, and the next concrete step.
</output>
