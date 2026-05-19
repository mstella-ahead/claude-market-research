# market-research

Parallel internal + external company research → 19-slide AI strategy proposal deck.

## What it does

When you run `/market-research:run <company>`:

1. Spawns an **internal-researcher** sub-agent that uses only Glean.
2. Spawns an **external-researcher** sub-agent that uses only public web sources.
3. Both run in parallel and write separate Markdown reports.
4. A **consolidator** sub-agent reconciles the two reports into structured JSON, flagging conflicts for human review.
5. After you review the flagged conflicts, the `strategy-deck` skill scores all strategic areas and produces a 19-slide PowerPoint deck.

## Components

- **Slash command**: `/market-research:run <company> [optional context]`
- **Skills**: `company-research` (orchestration), `strategy-deck` (deck generation)
- **Sub-agents**: `internal-researcher`, `external-researcher`, `consolidator`

## Required external setup

- A Glean MCP server connected and named exactly `glean_default` — in Claude Code via `claude mcp add glean_default <endpoint> --transport http --scope user`, or in Cowork as a Web connector (Customize → Connectors). See the repo [README](../../README.md#2-connect-the-glean-mcp-server) for full steps.

Without Glean, the plugin runs external-only with the missing internal context clearly flagged.

## Outputs

Written to `./runs/<company-slug>/`:

- `internal_report.md`
- `external_report.md`
- `consolidated_brief.json`
- `scoring_workings.md`
- `proposal.pptx`

## See also

The repo-level [README](../../README.md) has full installation instructions, architecture diagram, and customization guidance.
