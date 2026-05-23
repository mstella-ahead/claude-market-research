# bench/ — Claude vs Parallel.ai external-research benchmark

A one-time, throwaway-ish comparison of two implementations of the same task: producing an outside-in research report on a target company. Both implementations target the canonical schema at [`schema.json`](./schema.json).

This is **not** a migration. The Claude path stays in production unchanged. Everything under `bench/` exists to measure whether Parallel.ai's [Task API in Deep Research mode](https://docs.parallel.ai/task-api/examples/task-deep-research) could be a viable alternative for the external-research stage.

## What gets compared

| | Claude path | Parallel path |
|---|---|---|
| Implementation | `agents/external-researcher.md` sub-agent (production code) | Parallel `Task` API, `processor="pro"`, `output_schema=schema.json` |
| Entry point | `claude -p "/market-research:bench-external <company>"` | `bench/run.py` direct SDK call |
| Output (markdown) | `external_report.md` (same as production) | Rendered from JSON by a deterministic template in `run.py` |
| Output (JSON) | `external_report.json` conforming to `schema.json` | `result.output.content` (already JSON conforming to `schema.json`) |

## What's measured

Per provider, per company:

- **Wall-clock latency** (start of dispatch → outputs on disk)
- **Token usage** in/out (Claude path; from `claude -p --output-format json` response)
- **Task / token cost in USD** (using `pricing.json` and per-run metadata)
- **Success / error** boolean
- **Blind judge scores** (1–5) across five criteria: factual accuracy, citation quality, coverage breadth, recency, structural fidelity. See [`judge_schema.json`](./judge_schema.json).

Outputs land in `bench/results/<company>-<ISO_timestamp>/` with:

- `claude_output.{md,json}`
- `parallel_output.{md,json}`
- `metrics.json` (latency / tokens / cost / success per provider)
- `judge_scores.json` (blind A/B scores, verdict, de-anon mapping)
- `comparison.md` (side-by-side human-readable summary, close-calls flagged)

## How to run

> Phase 4+ — these instructions are stubs until the harness lands.

```bash
# 1. Install dependencies (the harness is local-only — no need to add to plugin)
python3 -m venv .venv && source .venv/bin/activate
pip install -r bench/requirements.txt

# 2. API keys: put ANTHROPIC_API_KEY and PARALLEL_API_KEY in .env at repo root
#    (already gitignored). Both bench/run.py and bench/judge.py load it via python-dotenv.

# 3. Single-company run (smoke test)
python bench/run.py --company "American Electric Power"

# 4. All three test companies (after smoke approval)
python bench/run.py --company "American Electric Power"
python bench/run.py --company "WEC Energy Group"
python bench/run.py --company "DaVita"

# 5. Roll-up across runs
python bench/run.py --summary
```

## Test set

See [`companies.yaml`](./companies.yaml). Three companies chosen to give one ground-truthable case (WEC — user has past runs) and one out-of-sector control (DaVita — kidney dialysis):

- **AEP** — American Electric Power, regulated electric utility
- **WEC** — WEC Energy Group, regulated electric utility
- **DaVita** — DaVita Inc, kidney dialysis services

## Hard rules

- **Same schema, both sides.** `schema.json` is the canonical contract. Neither implementation gets a custom schema. If a field is hard for one provider to populate, it stays in the schema — that *is* the signal we're measuring.
- **Blind judge.** The judge sees Output A / Output B with random assignment. The de-anon mapping is in `judge_scores.json` so a human can audit.
- **No silent reconciliation.** When the judge can't separate them, that's a "close call" — the bench surfaces it for human review rather than picking a winner.
- **Production code unchanged.** PR #1 (on `main`) makes the Claude external-researcher dual-write markdown + JSON. The consolidator continues reading markdown — the JSON path is purely additive.
