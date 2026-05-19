---
name: strategy-deck
description: Use this skill whenever the user wants to generate, build, or refresh the 19-slide AI strategy proposal deck from a consolidated research brief. Triggers include "generate the deck", "build the proposal deck", "create the strategy presentation", "make the pitch deck", or natural completion of the company-research skill. Produces a McKinsey-style PowerPoint with a 12-area strategic table, 2x2 prioritization matrix, wave sequencing, Wave 1 lever pack, and pilot scoring framework. Use this skill instead of writing slides freehand — the 19-slide structure encodes a proven story arc that breaks if you drift from it.
---

# Strategy Deck

This skill turns a consolidated research brief into a 19-slide AI strategy proposal deck.

## Required input

`consolidated_brief.json` (produced by the `company-research` skill / `consolidator` sub-agent). The path is typically `./runs/<company-slug>/consolidated_brief.json`.

If the brief doesn't exist, stop and tell the user — don't try to research the company yourself. Direct them to run `/market-research:run <company>` first.

## Required reading before generating slides

You MUST read these in order:

1. `references/slide_blueprints.md` — what each of the 19 slides contains, with example titles
2. `references/scoring_rubric.md` — how to score Impact and AI Readiness, and how to assign waves
3. `/mnt/skills/public/pptx/SKILL.md` — PowerPoint generation mechanics for this environment

Don't skip these. The blueprints contain non-obvious framing choices that aren't in the brief.

## Step-by-step

### Step 1: Read the brief

Read `consolidated_brief.json`. Confirm it has:
- 3–4 pillars
- ~10–12 strategic areas total
- A non-empty `company_summary`

If any of these are missing, ask the user whether they want to proceed anyway or rerun research.

### Step 2: Score every area

For each strategic area, apply the rubric in `references/scoring_rubric.md`:
- **Impact** rating: Very High / High / Medium / Low
- **AI Readiness** rating: High / Medium / Low

Write your full reasoning (not just the final ratings) to `./runs/<slug>/scoring_workings.md`. This is for the consultant to audit before sending the deck. The workings file matters as much as the deck — it's how the consultant defends the wave assignments in a client meeting.

### Step 3: Assign waves

Using the scores, assign each area to:
- **Wave 1** (3 areas): high impact + high readiness
- **Wave 2** (4 areas): high impact, more setup needed
- **Wave 3** (3 areas): medium impact or needs groundwork
- **Deprioritized** (2 areas): lower impact or partly solved

Target the distribution above. If the math doesn't work out (e.g., you have 5 areas that legitimately belong in Wave 1), document that in `scoring_workings.md` and pick the strongest 3.

### Step 4: Pick the Wave 1 anchor

From the 3 Wave 1 areas, designate one as the **anchor use case** — the area the proposal would suggest as Pilot #1. Selection criteria, in priority order:
1. Highest combined Impact × Readiness
2. Clearest data availability
3. Lowest change-management cost
4. Highest stakeholder visibility (because pilots that nobody sees don't build momentum)

Document the anchor selection rationale in `scoring_workings.md`.

### Step 5: Generate the deck

Follow `references/slide_blueprints.md` to produce each slide. Use the pptx skill mechanics for the actual file generation.

Style rules (don't violate these):

- **Titles are McKinsey-style: action-oriented sentences.** If you only read the titles in order, the proposal still makes sense. Examples: "Outside-in, we identified 12 strategic areas across four operational pillars," not "Strategic Areas".
- **Frame as "illustrating the approach", not "delivering a finished strategy."** Language like "outside-in, we identified..." and "here is how the areas could sequence..." rather than "we will do X for you."
- **Pair every AI lever in slide 12 with at least one traditional (non-AI) lever.** AI alone isn't enough — process improvements run alongside.
- **Ground objectives in real numbers** from `scale_metrics` in the brief when available.
- **Surface conflicts and low-confidence claims somewhere visible** — usually a footnote on slide 11 or an appendix note. Don't bury them.

### Step 6: Write outputs

Write to `./runs/<slug>/`:
- `proposal.pptx` — the deck
- `scoring_workings.md` — the audit trail of impact/readiness reasoning and wave assignments

### Step 7: Tell the user what to review

Don't just hand them the file. Surface specifically:

> "Generated `proposal.pptx` and `scoring_workings.md`.
> 
> Before sending, please review:
> - Wave assignments (slides 10–11) — these are model judgments; the rationale is in scoring_workings.md
> - The anchor use case selection (slide 12) — does this match what you'd lead with?
> - Slides 5–8 (methodology) — these are largely template; check they match your firm's actual phrasing
> - Conflicts flagged on slide [N] — confirm the framing is acceptable"

## Anti-patterns to avoid

- **Generating the deck before the user has reviewed the consolidated brief.** Conflicts and low-confidence claims should be resolved (or knowingly accepted) first.
- **Inventing scale metrics or pain points to make the slides look meatier.** If the brief doesn't have it, the slide doesn't get it. Better to have a slightly thin slide than a confidently wrong one.
- **Drifting from the 19-slide structure.** It's load-bearing. The story arc is: context → methodology → applied → adoption → next steps. Skipping or reordering breaks the flow.
- **Putting bullet text on every slide.** Many slides should be a single chart, table, or 2x2 with light annotation.
