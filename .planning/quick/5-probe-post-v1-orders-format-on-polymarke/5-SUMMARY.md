---
phase: quick
plan: 5
subsystem: polymarket-orders-schema
tags: [polymarket, orders, protobuf, schema-discovery, copy-trading]
dependency_graph:
  requires: [src/auth/polymarket_auth.py, src/platforms/polymarket.py]
  provides: [scripts/probe_polymarket_orders.py, .planning/research/copy_trading_research.md ORDER SCHEMA section]
  affects: [Polymarket.us live executor path — now known to require protobuf]
tech_stack:
  added: [requests (sync HTTP for probes)]
  patterns: [load_from_env() pattern, intentional-malformed-probe for schema discovery]
key_files:
  created: [scripts/probe_polymarket_orders.py]
  modified: [.planning/research/copy_trading_research.md]
decisions:
  - "POST /v1/orders on polymarket.us uses protobuf body format, not JSON"
  - "Empty body (Probe A) returned HTTP 500 business logic error — proto parse succeeded"
  - "JSON bodies (Probes B/C/D) returned HTTP 400 proto parse errors — schema mismatch"
  - "polymarket.COM path (py-clob-client) remains unblocked and is preferred path"
metrics:
  duration_minutes: 15
  completed_date: 2026-03-08
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Quick Task 5: Probe POST /v1/orders Format on Polymarket.us — Summary

**One-liner:** POST /v1/orders on polymarket.us requires protobuf body encoding (not JSON) — confirmed by live probe responses with explicit "proto: syntax error" messages.

## What Was Found

### The critical finding: protobuf body format

POST /v1/orders on polymarket.us is a gRPC-gateway endpoint that expects a protobuf-serialized
(proto3 JSON-mapped) request body. Standard `application/json` with arbitrary field names is
rejected with explicit proto parser errors.

Four probes were sent — none placed a real order:

| Probe | Body | HTTP | Response |
|-------|------|------|----------|
| A — empty `{}` | `{}` | 500 | `"market metadata is required"` |
| B — JSON marketId/float | `{"marketId":"...", "price":0.5}` | 400 | `proto: syntax error … unexpected token 0.5` |
| B2 — JSON tokenId/string | `{"tokenId":"...", "price":"0.50"}` | 400 | `proto: syntax error … unexpected token "0.50"` |
| B3 — JSON identifier/action | `{"identifier":"...", "price":0.5}` | 400 | `proto: syntax error … unexpected token 0.5` |

### Interpretation

Probe A is the most informative: an empty `{}` body PARSED SUCCESSFULLY as an empty protobuf
message (HTTP 500 is a business logic error, not a parse error). The server responded with
"market metadata is required" — meaning the empty proto message reached business logic, and
the first required field is something like `marketId`/`tokenId`/`identifier`.

Probes B-D all FAILED at the proto parser level — the JSON body structure did not conform to
proto3 JSON mapping rules. The float literal `0.5` caused a proto parse error, suggesting the
`price` field is not a float/double in the schema (likely an integer in cents, or a string).

### Activities endpoint

Only deposit and referral activities were found — the account has never placed a trade on
polymarket.us. The activity structure for trades would be visible after the first real copy
trade is placed.

## What the Order Schema Looks Like

**UNKNOWN in detail** — we confirmed the format is protobuf but do not have the `.proto` file.

What we know:
- Body format: proto3 JSON mapping (NOT raw JSON, NOT binary protobuf — gRPC-gateway hybrid)
- First required field: "market metadata" (marketId, tokenId, or identifier equivalent)
- Price field type: likely NOT float/double — integer cents or string decimal expected
- Field names: must match proto3 schema exactly (unknown camelCase aliases)

What we still need:
- The `.proto` schema file for the POST /v1/orders request message
- OR a captured working request from the iOS app (Charles Proxy / mitmproxy)
- OR documentation from the polymarket.us developer portal (if any)

## Next Concrete Step

**The polymarket.us path is blocked by the protobuf schema.**

The unblocked path is polymarket.COM:
- Uses py-clob-client with standard REST/JSON and ECDSA (Ethereum wallet) auth
- Whale data (data-api.polymarket.com) is already being collected from .COM
- Order format is well-documented (JSON) and the library handles signing
- Gate: Matthew creates polymarket.com account + Polygon wallet

If polymarket.us protobuf schema is still desired:
1. Use mitmproxy on an iOS device with the polymarket.us app to capture one real order request
2. Or check github.com/Polymarket org for any `.proto` files
3. The captured request gives us the complete working body structure

**Recommendation: proceed with polymarket.COM path (py-clob-client).** It does not have
this blocker, the whale data pipeline already reads .COM markets, and it gives access to
the full market catalog (politics, crypto, economics) where the whales actually trade.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | f3a3fef | feat(quick-5): add polymarket orders probe script |
| Task 2 | b0added | docs(quick-5): document POST /v1/orders protobuf schema findings |

## Self-Check

- [x] `scripts/probe_polymarket_orders.py` exists and runs to "=== PROBE COMPLETE ===" with no crashes
- [x] `.planning/research/copy_trading_research.md` contains `POST /v1/orders SCHEMA` section (count=1)
- [x] No real orders placed (Probe A returned business logic error, Probes B-D returned parse errors)
- [x] Implementation implication in research doc is concrete and actionable
- [x] Both commits exist: f3a3fef, b0added
