---
description: Benchmark-only — run the external-researcher sub-agent in isolation and stage its output for the Claude-vs-Parallel.ai comparison harness. Do not use in production.
argument-hint: <company-name>
---

# /market-research:bench-external — benchmark entry point

You are running the external-research stage **in isolation** for the company: $ARGUMENTS

This command is a **benchmark scaffold**. It is **not** part of the production `/market-research:run` pipeline — do not invoke the `company-research` skill, do not run the internal researcher, do not run the consolidator, do not generate a deck.

## What you do

1. **Compute the slug** as kebab-case of the company name (e.g., "American Electric Power" → `american-electric-power`).

2. **Ensure the run directory exists**: `./runs/<slug>/`. The external-researcher will write its outputs here.

3. **Dispatch the `external-researcher` sub-agent** via the Task tool with this prompt:

   > "Research the company '<NAME>' using the public web only. No optional context. Write your full report to `./runs/<slug>/external_report.md` and `./runs/<slug>/external_report.json` following the schema in your instructions. The JSON must conform to `bench/schema.json` at the repo root. When done, print 'EXTERNAL_RESEARCH_DONE' to stdout."

4. **Wait for the sub-agent to return.** Verify both files exist and are non-empty:
   - `./runs/<slug>/external_report.md`
   - `./runs/<slug>/external_report.json`

5. **Validate the JSON parses**:

   ```bash
   python3 -m json.tool ./runs/<slug>/external_report.json > /dev/null
   ```

6. **Stage the outputs for the harness.** Create `bench/results/claude/<slug>/` and copy both files there (do not move — leave `./runs/<slug>/` intact in case the human wants to inspect it):

   ```bash
   mkdir -p bench/results/claude/<slug>
   cp ./runs/<slug>/external_report.md   bench/results/claude/<slug>/external_report.md
   cp ./runs/<slug>/external_report.json bench/results/claude/<slug>/external_report.json
   ```

7. **Print a summary to stdout** for the harness to parse:

   ```
   BENCH_EXTERNAL_DONE
     company: <name>
     slug: <slug>
     md_path: bench/results/claude/<slug>/external_report.md
     json_path: bench/results/claude/<slug>/external_report.json
     md_bytes: <number>
     json_bytes: <number>
   ```

## Hard rules

- **No internal research.** Do not spawn `internal-researcher`. Do not call any Glean tool. The benchmark measures external-only research.
- **No consolidator.** This command produces raw external reports, not a brief.
- **No deck.** This command does not call `strategy-deck`.
- **Do not improvise.** Spawn `external-researcher` as written — do not do the research yourself.

## Failure modes

- **External-researcher returns but a file is missing or empty** → re-dispatch the sub-agent **once**. If it fails again, print `BENCH_EXTERNAL_FAILED` with the error and stop. The harness will record this as a failed run.
- **The JSON doesn't parse** → re-dispatch the sub-agent once with the parse error in the prompt so it can correct itself. If it fails again, print `BENCH_EXTERNAL_FAILED` with the JSON error and stop.
- **The company name is ambiguous** → do not stop to ask. The benchmark assumes the harness has already picked an unambiguous name. Proceed with whatever was passed.
