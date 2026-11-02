# opencode-usage

Token usage and estimated API-equivalent costs for the
[OpenCode CLI](https://github.com/anomalyco/opencode).

OpenCode stores sessions and messages locally. `opencode-usage` reads that
store and prints a **last-2-months**
token & cost breakdown, modeled on
[`ccusage`](https://github.com/ryoppippi/ccusage) and `antigravity-usage`
(zero-dependency single executable, live online pricing). One command, a compact
list, and a loading indicator while pricing is fetched.

```
📊 OpenCode Usage (last 2 months):
• 2026-04: 7,436,411 tokens, Cost: $2.72
• 2026-05: 86,282,310 tokens, Cost: $32.50
```

> Example output uses illustrative sample numbers, not real usage.

## Requirements

- Python 3.8+ (standard library only, **zero external dependencies**)
- A local opencode install that has produced at least one session

## Install

```bash
chmod +x opencode-usage
# optional: put it on your PATH
ln -sf "$(pwd)/opencode-usage" ~/.local/bin/opencode-usage
```

## Usage

```bash
opencode-usage
```

That's it, no flags, no subcommands. It always reports the current and previous
calendar month from `~/.local/share/opencode/opencode.db`.

## How it works

### Data source

Reads opencode's SQLite store at `~/.local/share/opencode/opencode.db`
(opened with SQLite `mode=ro`, which prevents database writes).
Per-assistant-message token counts, model, and timestamp are extracted from the
`session_message` table in OpenCode 2.x, or the legacy `message` table,
using their JSON `data` columns.

| Field | Source |
|-------|--------|
| input / output / reasoning / cache read / cache write tokens | `data.tokens.*` (both schemas) |
| provider / model | 2.x: `data.model.providerID` / `.id`; legacy: `data.providerID` / `.modelID` |
| timestamp (month grouping) | `data.time.created` (unix ms) |

The reported `tokens` value is the sum of every token type for that month.

### Pricing

Cost is computed with **[models.dev](https://models.dev)**, the same pricing
source opencode uses internally, using the token-cost formula in OpenCode 2.x
(`packages/core/src/session/usage.ts`):

```
cost = (input·in + output·out + reasoning·out
        + cache_read·cache_read + cache_write·cache_write) / 1_000_000
```

Reasoning tokens use the output rate. The report estimates API-equivalent
cost at current catalog rates, rather than reading recorded charges or
reconstructing historical invoices.

Pricing is **fetched fresh from models.dev on every run** so cost always reflects
current rates. The on-disk cache at `~/.cache/opencode-usage/models-dev.json` is
written after each successful fetch and used **only** as an automatic fallback
when the live fetch fails (offline); in that case a `pricing is STALE` warning is
printed. If neither live nor cached pricing is available, cost is shown as
`unknown` rather than a misleading `$0.00`.

Rates are resolved from models.dev. Subscription providers can list zero
per-token prices; the report estimates API-equivalent cost using these tiers:

1. The source provider's own rate (happy path, usually nonzero already).
2. The **twin provider**: source with plan/region suffixes stripped
   (`-coding-plan`, `-token-plan`, `-plan`, `-cn`, recursively). This is the
   natural pay-as-you-go equivalent of a subscription plan
   (e.g. `zai-coding-plan` → `zai`).
3. The **median rate** across all paid providers serving the same model id.
   Median, not max, so a single outlier listing (one provider charging 5x
   market) cannot dominate the fallback.

This is fully generic: no provider or model names are hardcoded, so it works
whether you use 2 models or 2,000. Models that exist nowhere in models.dev are
still counted in tokens; their month displays `Cost: unknown`.

## Verification

- Token fields are read from the selected schema, including reasoning and cache usage.
- Cost formula matches opencode's native computation, including the reasoning
  term charged at the output rate.
- `$0` subscription models resolve via twin-provider then median rate across
  paid providers (see "Pricing" above).
- Offline run falls back to cached pricing with a `STALE` warning; if no cache
  exists either, cost is shown as `unknown` rather than a misleading `$0.00`.
- Missing DB is handled with a clear error.
- DB file mtime is unchanged after runs (read-only access confirmed).

## License

MIT, see [LICENSE](LICENSE).

## CLI compatibility and checks

Run regression checks with `python3 -m unittest discover -v` and syntax checks
with `python3 -m py_compile opencode-usage test_usage.py`. No typechecker is configured.

OpenCode 2.x SQLite stores use `session_message` and nested model identity.
When that table exists it is authoritative; otherwise the legacy `message`
table is used. Costs remain API-equivalent estimates. Months with unpriced
models display `unknown`.

This tool supports OpenCode CLI 2.x and legacy SQLite stores. OpenCode shares
its database across clients: records do not reliably identify the originating
client, so totals can include desktop activity. CLI-only describes supported
operation, not guaranteed filtering by originating client.
