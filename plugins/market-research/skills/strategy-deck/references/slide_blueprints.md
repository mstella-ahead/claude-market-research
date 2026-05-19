# Slide Blueprints — 19-slide AI Strategy Proposal Deck

The deck has a fixed structure. Each slide below specifies content, the title style, and what comes from the consolidated brief. Sample titles are illustrative — adapt them to the specific client, keeping the McKinsey action-oriented style.

## Story arc overview

```
1     Title
2     Agenda
3     Context (we're showing our approach, not selling a ready-made strategy)
4     ── Section divider: Methodology ──
5–8   Methodology
9–13  Applied to the client (THE CORE)
  9   12 strategic areas table
  10  Prioritization matrix (2x2)
  11  Wave sequencing table
  12  Wave 1 lever pack
  13  Initiative scoring framework for pilot selection
14    ── Section divider: Adoption ──
15–16 Adoption & change management
17    ── Section divider: Next steps ──
18    Next steps
19    Thank you
```

---

## Slide 1 — Title

- Client name and logo (logo optional; many decks skip it for IP reasons)
- Engagement framing: "AI Strategy Proposal" or "An illustrative approach to AI-enabled transformation"
- Firm name, date

Example title: `An illustrative approach to AI-enabled transformation at <Client>`

---

## Slide 2 — Agenda

Three or four sections matching the deck structure:
1. Our approach
2. Applied to <Client>: strategic areas, prioritization, and pilot framing
3. Adoption and change management
4. Proposed next steps

No content beyond the agenda. Single-color list.

---

## Slide 3 — Context

The most-misread slide if done wrong. Explicit framing:

- This deck **illustrates an approach**, not a finished strategy
- The 12 areas were identified **outside-in from public information** plus our firm's internal POVs
- A real engagement would validate everything with the client's actual data and stakeholders
- The goal of this conversation: agree on the methodology and pick a pilot

2-sentence company summary from `consolidated_brief.json` → `company_summary`. Plus the 2–3 most relevant scale metrics from `scale_snapshot`.

Example title: `Outside-in, here is what an AI strategy engagement could look like for <Client>`

---

## Slide 4 — Section divider: Methodology

Visual section break. One sentence framing the next 4 slides.

Example title: `Our approach: four steps from operational mapping to pilot selection`

---

## Slide 5 — Methodology step 1: Operational mapping

How we group operations into pillars (3–4 typical), and how strategic areas sit within pillars (3 areas per pillar typical).

Generic — does not need client-specific content. Use a simple visual showing Pillar → Area → Use case hierarchy.

---

## Slide 6 — Methodology step 2: Impact × AI Readiness scoring

Define the two axes:
- **Impact**: operational efficiency gain, customer/member experience lift, cost reduction, compliance risk mitigation
- **AI Readiness**: rule-based? repetitive? high-frequency? structured data? handover count?

Show the 2x2 grid as a generic template (no client data yet — that's slide 10).

---

## Slide 7 — Methodology step 3: Wave sequencing

Define the four waves:
- **Wave 1** — high impact + high readiness (3 areas)
- **Wave 2** — high impact, more setup needed (4 areas)
- **Wave 3** — medium impact or groundwork needed (3 areas)
- **Deprioritized** — lower impact or partly solved (2 areas)

One sentence on why this distribution: focus + sequencing + realistic capacity.

---

## Slide 8 — Methodology step 4: Pilot selection criteria

15+ criteria across categories:
- Strategic priority
- Data readiness
- Complexity
- Change management
- Stakeholder buy-in
- Compliance

Brief description; the full rubric appears later on slide 13 with scoring applied.

---

## Slide 9 — Applied: 12 strategic areas

The first "applied" slide. A single table:

| Pillar | Strategic Area | Objective | Impact Potential |
|---|---|---|---|
| Pillar 1 | Area 1 | One-sentence objective grounded in scale metric if available | Very High |
| ... | ... | ... | ... |

Source: `consolidated_brief.json` → pillars[].areas[]
Impact rating: from this skill's scoring (Step 2)

Example title: `Outside-in, we identified 12 strategic areas across four operational pillars`

---

## Slide 10 — Prioritization matrix (2x2)

Plot all 12 areas on Impact (x-axis) × AI Readiness (y-axis).

Four quadrants labeled Wave 1 / Wave 2 / Wave 3 / Deprioritized. Each area appears as a labeled dot or numbered marker.

Example title: `Plotting impact against readiness reveals three Wave 1 candidates`

---

## Slide 11 — Wave sequencing table

All 12 areas with full reasoning:

| Area | Impact | Why (1 sentence) | AI Readiness | Why (1 sentence) | Wave |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

This is the most evidence-heavy slide. The "Why" columns are essential — they ground the ratings in client-specific operations from the brief.

Footnote on this slide: any `conflicts_for_human_review` items relevant to the rankings.

Example title: `Wave 1 prioritizes high-impact, high-readiness areas; Wave 2 builds the foundation`

---

## Slide 12 — Wave 1 lever pack

For each of the 3 Wave 1 areas, a card with:

- **AI levers**: 2–3 specific AI use case examples
- **Traditional levers**: 2–3 non-AI process improvements (NEVER omit this — AI alone isn't enough)
- **Primary outcome**: the one metric this should move

Star the **anchor use case** (Pilot #1 candidate).

Example title: `Wave 1 pairs AI levers with traditional process improvements to compound impact`

---

## Slide 13 — Initiative scoring framework

A scoring table that applies the criteria from slide 8 to each Wave 1 area, surfacing the anchor use case as the recommended Pilot #1.

| Criterion | Weight | Area A | Area B | Area C |
|---|---|---|---|---|
| Strategic priority | ... | ... | ... | ... |
| Data readiness | ... | ... | ... | ... |
| Complexity (inverse) | ... | ... | ... | ... |
| Change management ease | ... | ... | ... | ... |
| Stakeholder buy-in | ... | ... | ... | ... |
| Compliance risk (inverse) | ... | ... | ... | ... |
| ... (15+ criteria total) | | | | |
| **Total** | | **A** | **B** | **C** |

Highlight the winning column. Brief commentary: why this one as Pilot #1.

Example title: `Applying our scoring framework, <Anchor Use Case> emerges as Pilot #1`

---

## Slide 14 — Section divider: Adoption

Example title: `Picking the right pilot is half the work — adoption is the other half`

---

## Slide 15 — Adoption: change management

The model: stakeholder identification → communication plan → training plan → success metrics → governance.

Light client-specific tailoring if the brief mentions specific stakeholders or org sensitivities; otherwise generic.

---

## Slide 16 — Adoption: operating model evolution

How the team and operating model evolve as AI capabilities mature:
- Phase 1: human-led with AI augmentation
- Phase 2: AI-led with human review
- Phase 3: human-on-the-loop oversight for steady-state operations

Honest about the timeline (often 18–36 months for a real enterprise rollout).

---

## Slide 17 — Section divider: Next steps

Example title: `Where we would go from here`

---

## Slide 18 — Next steps

Concrete proposed next steps. Usually:
1. A discovery workshop to validate the 12 areas with the client's actual data
2. A focused 6–8 week pilot on the anchor use case
3. Decision points at the end of pilot

Include rough timeline and a sense of who would be involved.

---

## Slide 19 — Thank you

Contact info, firm logo, optional "Questions?" prompt.

---

## Common cross-slide rules

- **Footers**: client name + date + "Illustrative — outside-in" disclaimer on slides 9–13
- **Source citations**: when a slide cites a specific external fact, footnote the source
- **Conflicts**: any `conflicts_for_human_review` flagged in the brief should appear in a visible footnote on the relevant slide
- **Numbers**: always include the year and source for any scale metric on a slide
- **Slides 5–8** are the most reusable; slides 9–13 are the most client-specific
