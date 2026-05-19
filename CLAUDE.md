# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is a **Claude Code / Cowork plugin marketplace**, not an application. It ships one plugin, `market-research`, made entirely of Markdown instruction files and JSON manifests. There is **no build step, no test suite, no compiled code, and no runtime dependencies** — "editing the code" here means editing prompts (agent/skill/command Markdown) and their frontmatter.

The plugin runs parallel internal (Glean) + external (web) research on a company and generates a 19-slide AI strategy deck.

## Validating changes

There is no `make`/`npm`/lint. The only mechanical checks worth running:

```bash
# Validate the two JSON manifests parse
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool plugins/market-research/.claude-plugin/plugin.json >/dev/null
```

Functional testing happens only inside Claude Cowork / Claude Code by installing the marketplace and running `/market-research:run <company>`. You cannot exercise the pipeline from this repo directly — it depends on the Glean MCP connector and the host skill `/mnt/skills/public/pptx/SKILL.md`.

## Two-level plugin structure

`.claude-plugin/marketplace.json` is the **marketplace** manifest — it declares which plugins exist and where their source lives. `plugins/market-research/.claude-plugin/plugin.json` is the **plugin** manifest. A fork must replace the placeholder owner strings (`Miltos Stella`, `mstella-ahead`) in *both* files.

## The pipeline (the big picture)

`/market-research:run` (command) → `company-research` skill (orchestrator) → two sub-agents in parallel → `consolidator` sub-agent → `strategy-deck` skill → `proposal.pptx`.

```
commands/run.md            entry point; forces use of the company-research skill
skills/company-research    orchestrator: dispatches sub-agents, never researches itself
agents/internal-researcher Glean MCP tools ONLY  → runs/<slug>/internal_report.md
agents/external-researcher Web tools ONLY        → runs/<slug>/external_report.md
agents/consolidator        reconciles both       → runs/<slug>/consolidated_brief.json
skills/strategy-deck       scores + builds deck  → runs/<slug>/proposal.pptx + scoring_workings.md
```

## Load-bearing invariants — do not break these

1. **Tool isolation between researchers.** `internal-researcher` and `external-researcher` have deliberately **non-overlapping `tools:` frontmatter lists**. Internal gets `mcp__glean__*` only; external gets `WebSearch`/`WebFetch` only. This isolation is the entire reason the plugin exists (it prevents anchoring bias). If you edit either `tools:` list, you are changing a core guarantee — never give one researcher the other's tools, and never pass one's findings to the other.

2. **Parallel dispatch.** The orchestrator must spawn both researchers with two Task calls **in the same turn**. The instructions in `commands/run.md` and `skills/company-research/SKILL.md` enforce this; keep them consistent if you touch one.

3. **File-path + schema contracts between stages.** Each stage reads/writes specific files at `./runs/<company-slug>/` with schemas defined inline in the prompts:
   - `internal_report.md` / `external_report.md` schemas live in the agent files; the consolidator's reconciliation rules assume them.
   - `consolidated_brief.json` schema lives in `agents/consolidator.md`; it is consumed by `skills/strategy-deck/SKILL.md` and `references/slide_blueprints.md` (which reference fields like `pillars[].areas[]`, `company_summary`, `scale_snapshot`, `conflicts_for_human_review`).
   Changing a schema in one place requires updating every downstream consumer — they are coupled by convention, not by code.

4. **Conflicts are surfaced, never silently resolved.** The consolidator flags disagreements into `conflicts_for_human_review`; the orchestrator pauses for human review; the deck footnotes them. Don't add logic that auto-resolves conflicts.

5. **The 19-slide deck structure is fixed.** `references/slide_blueprints.md` defines a load-bearing story arc (context → methodology → applied → adoption → next steps). Adding/removing/reordering slides breaks it.

## Where to make different kinds of change

- **Scoring logic** (Impact / AI Readiness ratings, wave assignment) → `skills/strategy-deck/references/scoring_rubric.md`
- **Slide content/titles/structure** → `skills/strategy-deck/references/slide_blueprints.md`
- **What each researcher looks for** → the respective `agents/*-researcher.md`
- **Orchestration flow** → `skills/company-research/SKILL.md` and `commands/run.md` (keep these two in sync)

These reference files are loaded by the skill at runtime, so changes take effect with no rebuild.

## Outputs are never committed

`runs/` and `*.pptx`/`*.xlsx`/`*.docx` are gitignored — they contain client research. Do not commit anything under `runs/`.
