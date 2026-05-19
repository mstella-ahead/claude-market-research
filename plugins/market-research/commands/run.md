---
description: Run parallel market research on a company and produce a 19-slide AI strategy proposal deck
argument-hint: <company-name> [optional context]
---

Run the full market-research pipeline for: $ARGUMENTS

You MUST use the `company-research` skill to plan and execute this work. Do not improvise the orchestration — the skill exists precisely to enforce strict isolation between internal and external research streams.

High level, the skill will:
1. Spawn the `internal-researcher` sub-agent (Glean tools only) AND the `external-researcher` sub-agent (web tools only) IN THE SAME TURN, so they execute in parallel.
2. Wait for both to write their reports to `./runs/<company-slug>/`.
3. Invoke the `consolidator` sub-agent to produce `consolidated_brief.json`.
4. Pause and ask the user to review any conflicts the consolidator flagged.
5. Once the user is happy with the brief, use the `strategy-deck` skill to generate `proposal.pptx`.

Critical rules:
- Never pass internal findings to the external researcher, or vice versa.
- Never let the orchestrator do the research itself — always delegate to the sub-agents so isolation is preserved.
- If Glean MCP is not connected, surface that explicitly to the user and offer to proceed external-only with a clearly-flagged gap.

All outputs go to `./runs/<kebab-case-company-name>/`.
