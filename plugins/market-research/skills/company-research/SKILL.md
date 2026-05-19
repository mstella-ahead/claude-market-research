---
name: company-research
description: Use this skill whenever the user asks to research a company for an AI strategy engagement, build a market-research dossier, prepare for a client pitch, or invokes the /market-research:run command. Triggers include phrases like "research <company>", "build a dossier on <company>", "client research", "due diligence on <company>", "AI use cases for <company>", or "outside-in look at <company>". This skill orchestrates strictly-isolated parallel internal (Glean) + external (web) research streams via dedicated sub-agents and produces a consolidated brief ready for downstream deck generation. Use it instead of doing research yourself — the isolation it enforces is the whole point.
---

# Company Research

This skill orchestrates parallel, isolated internal + external research on a target company and produces a consolidated brief.

## Why this exists

Single-thread research causes anchoring bias: whichever source the agent looks at first colors the rest. To avoid that, internal research (via Glean) and external research (via web) run in two separate sub-agents with non-overlapping toolsets. Their reports are then reconciled by a third sub-agent that flags conflicts rather than silently resolving them.

**Do not skip the parallel dispatch. Do not do research yourself.** The isolation between sub-agents is the whole point of this workflow.

## Inputs

- `<company-name>` (required)
- Optional context: anything like "they're a TPA in Wisconsin focused on self-funded employers" or "we're pitching them on member-experience AI". Pass through to both sub-agents.

## Step-by-step

### Step 1: Preflight checks

- Verify Glean MCP is connected. The simplest test: list available MCP tools and check for `mcp__glean__*`. If absent, tell the user:

  > "Glean MCP isn't connected. To get the internal research stream, open Claude Desktop → Customize → Connectors → add Glean. Want me to proceed external-only for now? I'll clearly flag the missing internal context in the brief."

- Compute the company slug as kebab-case of the company name (e.g., "Acme Benefits Inc" → "acme-benefits-inc").

### Step 2: Create the run directory

```
./runs/<company-slug>/
```

### Step 3: Dispatch both researchers IN PARALLEL

This is the critical step. Spawn both sub-agents using two Task tool calls **in the same assistant turn** so they execute concurrently. Do NOT await one before starting the other.

For `internal-researcher`, the prompt is:

> "Research the company '<NAME>' using Glean only. Optional context: <CONTEXT or 'none provided'>. Write your full report to `./runs/<slug>/internal_report.md` following the schema in your instructions. When done, print 'INTERNAL_RESEARCH_DONE' to stdout."

For `external-researcher`, the prompt is:

> "Research the company '<NAME>' using the public web only. Optional context: <CONTEXT or 'none provided'>. Write your full report to `./runs/<slug>/external_report.md` following the schema in your instructions. When done, print 'EXTERNAL_RESEARCH_DONE' to stdout."

**Hard rule:** do not pass either sub-agent any content from the other. Pass them only the company name and the user-provided context.

### Step 4: Verify both reports exist

After both sub-agents return, check that:
- `./runs/<slug>/internal_report.md` exists and is non-empty
- `./runs/<slug>/external_report.md` exists and is non-empty

If either is missing or empty, re-dispatch that one sub-agent only (not both — preserve the work that succeeded).

### Step 5: Run the consolidator

Spawn the `consolidator` sub-agent with this prompt:

> "Reconcile the internal and external reports for '<NAME>' (slug: <slug>) into `./runs/<slug>/consolidated_brief.json`. Follow your schema exactly."

### Step 6: Surface the brief to the user

Read `consolidated_brief.json` and give the user a concise summary:

```
Brief complete: ./runs/<slug>/consolidated_brief.json

Pillars identified: <list>
Strategic areas: <n total across pillars>
Conflicts flagged for review: <n>
Low-confidence claims: <n>
Open questions: <n>
```

If `conflicts_for_human_review` is non-empty or any individual pillar has fewer than 2 areas, ask the user:

> "I'd recommend resolving the flagged conflicts before generating the deck. Want to walk through them now, or proceed and note them on the deck?"

### Step 7: Hand off to deck generation (when ready)

Once the user is OK with the brief (or has edited it directly), trigger the `strategy-deck` skill to produce `proposal.pptx`. Pass it the path to `consolidated_brief.json`.

## Failure modes and what to do

- **Glean MCP not connected** → see Step 1. Don't fake it; proceed external-only with a clear flag.
- **Both researchers find very little** → Don't fabricate. Produce a thin brief with explicit "data scarce" flags. Tell the user. The deck skill knows how to render this honestly ("outside-in we identified… but recommend follow-up validation").
- **External sub-agent hits rate limits or blocked pages** → It should note these and move on. Surface to user as gaps, not failures.
- **The two reports look like they're about different companies** → Stop. Tell the user. This usually means the company name was ambiguous (e.g., a holdco vs. subsidiary, or a name collision). Ask which entity they meant.

## Anti-patterns to avoid

- Reading the reports yourself and synthesizing without the consolidator. The consolidator's structured JSON output is what the deck skill needs.
- Asking the user to "just confirm" the brief without showing them the conflicts. Conflicts are the highest-value part of the output.
- Trying to be helpful by adding facts you "know" about the company. If it's not in one of the reports, it doesn't go in the brief.
