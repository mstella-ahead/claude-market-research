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

1. **Tool isolation between researchers.** `internal-researcher` and `external-researcher` have deliberately **non-overlapping `tools:` frontmatter lists**. Internal gets `mcp__glean_default__*` only; external gets `WebSearch`/`WebFetch` only. This isolation is the entire reason the plugin exists (it prevents anchoring bias). If you edit either `tools:` list, you are changing a core guarantee — never give one researcher the other's tools, and never pass one's findings to the other.

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

## Known gotchas

**Glean MCP is configured per-user, not in this repo.** There is intentionally no `.mcp.json` in the plugin. Glean MCP uses OAuth-via-SSO which is per-user — embedding the server URL here would break for any installer who hasn't pre-authorized it. Each user wires Glean themselves: in Claude Code via `claude mcp add glean_default <endpoint> --transport http --scope user`, or in Cowork as a Web connector (Customize → Connectors). Don't "fix" this by adding `.mcp.json`.

**The Glean MCP server must be named `glean_default`.** `agents/internal-researcher.md` declares its tools as `mcp__glean_default__*` — that namespace *is* the MCP server name. Name the server anything else and the agent's tools silently resolve to nothing, so `internal_report.md` comes back empty with no error. Like the sub-agent-name gotcha below, this name is load-bearing string-coupling. `glean_default` is Glean's own documented default, so the plugin standardizes on it. Its four wired tools — `search`, `chat`, `read_document`, `employee_search` — must be real Glean MCP tool names; check the server's tool list before adding more.

**Sub-agent names are referenced by string.** Each agent file's `name:` frontmatter (`internal-researcher`, `external-researcher`, `consolidator`) is what the orchestrator passes to the Task tool. Renaming an agent requires updating `skills/company-research/SKILL.md` where those names appear in the dispatch prompts.

**The plugin name is the slash command namespace.** Currently `/market-research:run`. Renaming the plugin in `plugin.json` changes every slash invocation; `marketplace.json` must match.

**Deck rendering depends on the host pptx skill.** `skills/strategy-deck` delegates the actual `.pptx` build to `/mnt/skills/public/pptx/SKILL.md` (built into Cowork/Claude Code). For firm-specific branding the right hook is a template `.pptx` under `skills/strategy-deck/assets/`, referenced from `SKILL.md` — don't reimplement pptx generation.

## Open enhancements (in priority order)

1. **Disambiguation pre-check.** Before dispatching the parallel sub-agents, do one quick web search to confirm the entity and ask the user to confirm. Prevents running the full pipeline on the wrong company for ambiguous inputs ("AEP", "TPA", common abbreviations). Add as a Step 1.5 in `skills/company-research/SKILL.md` between "Create the run directory" and "Dispatch both researchers."

2. **More aggressive people-search in `internal-researcher`.** Finding internal experts who already know the company or sector is the single highest-ROI Glean query for consulting work. The current prompt lists it as one of five searches; it should be a *required first* search with explicit instructions to surface 3+ relevant people before moving on.

3. **Tie-breakers for over-subscribed Wave 1.** The current rubric handles under-supply (fewer than 3 strong Wave 1 candidates) but the more common real-world case is over-supply (5+ areas legitimately score top-right). Add explicit tie-breakers to `scoring_rubric.md`: data freshness, stakeholder buy-in proxy, prior delivery track record on similar work.

4. **Sector-specific scoring rubric variants.** After 3–5 real-client runs, patterns will emerge (regulated industries weight compliance very differently). Split `scoring_rubric.md` into `scoring_rubric_generic.md` plus `_healthcare.md`, `_finance.md`, etc. Skill picks based on inferred sector from the brief.

## Calibration

The honest test isn't "did it produce a deck" — it's "would I send this deck." Expect 2–3 rounds of prompt tuning before output crosses that bar on a real client. Diagnostics to check after each run:

- Does `internal_report.md` find things you *know* exist in Glean? (Tests internal-researcher's search aggression.)
- Does `external_report.md` miss anything obvious? (Tests external-researcher's coverage.)
- Does the consolidator flag conflicts you expected, or paper them over? (Most common failure mode — silent reconciliation.)
- Are wave assignments defensible? Read `scoring_workings.md` and ask: would I stand behind these in a client meeting?

## Things deliberately not built — don't add without thinking

- **No `.mcp.json`** — see Glean MCP gotcha above.
- **No hardcoded .pptx template** — branding is firm-specific; left as a customization point under `skills/strategy-deck/assets/`.
- **No formal evals/test set** — useful for v0.2 once 3+ real example runs exist to evaluate against. Premature before then.
- **No third research thread** — a "third source" (SEC filings, court records, etc.) is tempting but each new thread compounds reconciliation complexity quadratically. Stay with two threads until the consolidator is reliably good on two.
