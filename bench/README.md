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

### Expectations

Budget **~$2.21 (Claude) + $0.10 (Parallel) per company-run**; **~7 min wall time per provider** (Claude ~6.4 min mean, Parallel pro ~8.1 min mean). A full 3-company sweep is therefore ~$7 and ~45 min wall-clock end-to-end (serial). Numbers derived from the 2026-05-24 runs recorded in `bench/results/`.

## How to run

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

# 5. Re-judge an existing run dir without re-invoking either provider
#    (use when the judge step failed but provider outputs are intact)
python bench/run.py --judge-only bench/results/<slug>-<timestamp>

# 6. Roll-up across runs
python bench/run.py --summary
```

## Gotchas

- **`claude -p` env-key precedence.** The harness scrubs `ANTHROPIC_API_KEY` (plus `CLAUDE_API_KEY` and `ANTHROPIC_AUTH_TOKEN`) from the subprocess env before spawning `claude -p` (commit `ded6def`). Reason: `claude -p` prefers an env-var API key over its OAuth login, and the `.env` file holds a console-issued API key that's a different account from the user's interactive OAuth — leaving it set causes an immediate 401 (`invalid x-api-key`). The judge still sees the key in `os.environ` so its direct SDK call works.
- **Top-level Claude token counts under-report.** `claude -p --output-format json` returns the parent session's tokens (a few hundred), not the spawned sub-agent's. `total_cost_usd` is correct; per-token attribution isn't. Treat the cost field as the load-bearing number.
- **Parallel's JSON Schema subset.** No `pattern` or `format` keywords on `output_schema`; encode constraints in field descriptions instead. The shared `schema.json` is already compliant.

## Test set

See [`companies.yaml`](./companies.yaml). Three companies chosen to give one ground-truthable case (WEC — user has past runs) and one out-of-sector control (DaVita — kidney dialysis):

- **AEP** — American Electric Power, regulated electric utility
- **WEC** — WEC Energy Group, regulated electric utility
- **DaVita** — DaVita Inc, kidney dialysis services

## Hard rules

- **Same schema, both sides.** `schema.json` is the canonical contract. Neither implementation gets a custom schema. If a field is hard for one provider to populate, it stays in the schema — that *is* the signal we're measuring.
- **Blind judge as of commit `a4e6ee7`.** The judge sees Output A / Output B with random assignment, and provenance markers (`researcher`, `generated_at`, the matching markdown header lines) are redacted before the prompt is built. The first-batch runs (2026-05-24) had partial provenance leaks fixed in that commit — see CLAUDE.md "Past experiments" for the caveat. The de-anon mapping is in `judge_scores.json` so a human can audit.
- **No silent reconciliation.** When the judge can't separate them, that's a "close call" — the bench surfaces it for human review rather than picking a winner.
- **Production code unchanged.** PR #1 (on `main`) makes the Claude external-researcher dual-write markdown + JSON. The consolidator continues reading markdown — the JSON path is purely additive.

## See also

- [`CLAUDE.md` → "Past experiments"](../CLAUDE.md#past-experiments) for the recorded verdict and the recommendation that came out of this benchmark.
- [`bench/results/summary-20260524T182733Z.md`](./results/summary-20260524T182733Z.md) for the rolled-up 3-company scores.
- Per-company artifacts under `bench/results/<slug>-<timestamp>/`: `comparison.md`, `judge_scores.json`, `metrics.json`, plus both providers' `.md` / `.json` outputs and Parallel's `parallel_basis.json`.
