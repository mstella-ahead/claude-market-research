# Scoring Rubric — Impact & AI Readiness

Use this rubric to score every strategic area in `consolidated_brief.json`. Write the full reasoning to `scoring_workings.md` — not just the final letter grades. Consultants need to defend these ratings in client meetings, and "the model decided" is not a defensible answer.

---

## Impact rating

Rate each area on a four-point scale based on the combined signal across four dimensions. **A single very strong dimension can lift the rating; a single very weak one rarely sinks it.**

### Dimensions

1. **Operational efficiency gain** — How much time, cost, or volume could this address? Anchor in real numbers from `scale_metrics` when available.
2. **Customer / member / user experience lift** — How visible is this to the end customer? Does it touch a key moment of truth (onboarding, claim, support)?
3. **Cost reduction** — Direct dollar savings, FTE reduction, or unit-economics improvement. Distinguish hard savings (visible in the P&L) from soft savings (capacity freed up).
4. **Compliance / risk mitigation** — Does it reduce regulatory exposure, audit findings, or reputational risk?

### Levels

| Rating | When to assign |
|---|---|
| **Very High** | Multi-dimensional impact, including at least one quantifiable big-number dimension (e.g., touches >20% of operating cost, or a clear regulatory exposure). Visible at C-suite level. |
| **High** | Strong on 1–2 dimensions with credible quantification. Visible at function-head level. |
| **Medium** | Real impact but contained (one team, one process). Hard to make a CFO-level case. |
| **Low** | Marginal, edge-case, or already partly solved. Doesn't make the top-10 list. |

### Quick gut check

If a senior partner can't summarize the impact in one sentence with a number in it, it's probably not Very High.

---

## AI Readiness rating

Three-point scale. AI readiness is about **how well the underlying process suits AI today**, not about whether AI is interesting in principle.

### Dimensions

1. **Rule-based vs. judgment-heavy** — More rules + fewer exceptions → higher readiness.
2. **Repetition & volume** — High-frequency, repetitive work → higher readiness. (Low-volume, bespoke work has poor ROI on AI even if technically feasible.)
3. **Standardization** — Same inputs, same outputs, same vocabulary across instances → higher readiness. Lots of variation → lower readiness.
4. **Data accessibility** — Is the data structured? Centralized? Cleanly labeled? Or scattered across PDFs, emails, and three legacy systems?
5. **Handover count** — Fewer human-to-human handovers in the current process → higher readiness. (Each handover is a place AI has to integrate.)
6. **External dependencies** — Does the process depend on third parties whose behavior the client can't change (regulators, broker portals, partner APIs)? More external dependencies → lower readiness.

### Levels

| Rating | When to assign |
|---|---|
| **High** | Rule-based, high-volume, structured data, few handovers, low external dependency. The classic "obvious AI candidate" — claims first-pass review, document classification, FAQ resolution. |
| **Medium** | Mixed signal: e.g., high volume and structured data but lots of judgment, OR clear rules but unstructured data, OR good fundamentals but heavy regulatory oversight. Most areas land here. |
| **Low** | Judgment-heavy, low volume, unstructured/scattered data, many handovers, or heavily regulated in a way that constrains AI use. AI can still help eventually but needs significant groundwork. |

---

## Wave assignment matrix

After scoring both axes, assign waves:

| | AI Readiness: High | AI Readiness: Medium | AI Readiness: Low |
|---|---|---|---|
| **Impact: Very High** | Wave 1 | Wave 2 | Wave 2 (with foundation work) |
| **Impact: High** | Wave 1 | Wave 2 | Wave 3 |
| **Impact: Medium** | Wave 2 | Wave 3 | Wave 3 / Deprioritize |
| **Impact: Low** | Wave 3 | Deprioritize | Deprioritize |

### Target distribution

- **Wave 1**: 3 areas
- **Wave 2**: 4 areas
- **Wave 3**: 3 areas
- **Deprioritized**: 2 areas

### Tie-breaking when too many areas qualify for the same wave

In priority order:
1. **Cleaner data wins.** Wave 1 needs to ship — pick areas where data won't be the blocker.
2. **Lower change-management cost wins.** Wave 1 needs adoption.
3. **Higher visibility wins.** A successful pilot that nobody sees doesn't compound.

### Tie-breaking when too few areas qualify for Wave 1

This is more common than the reverse. If only 1–2 areas clearly qualify:
- Look at the high-readiness pile — promote the one with the strongest *secondary* impact dimension.
- Or accept a Wave 1 of 2 areas and document why in `scoring_workings.md`. The structure isn't sacred — explaining a thin Wave 1 honestly is better than promoting a marginal area.

---

## Anchor use case selection (Pilot #1)

From the 3 Wave 1 areas, designate one as the **anchor**. Criteria in priority order:

1. Highest combined Impact × Readiness score
2. Clearest data availability today (not "after a migration")
3. Lowest change-management cost (touches fewer teams, less retraining)
4. Highest stakeholder visibility (someone senior cares about the outcome)
5. Best fit with our firm's POVs and prior wins (lower delivery risk)

Document the rationale in `scoring_workings.md`. A senior partner should be able to read it and immediately understand why this area, not the other two.

---

## Required writing in scoring_workings.md

For every area:

```markdown
### <Area name>
- **Impact: <rating>**
  - Operational efficiency gain: <evidence>
  - Customer experience lift: <evidence>
  - Cost reduction: <evidence>
  - Compliance / risk: <evidence>
  - **Why this rating overall**: <1–2 sentences>

- **AI Readiness: <rating>**
  - Rule-based vs. judgment: <evidence>
  - Repetition & volume: <evidence>
  - Standardization: <evidence>
  - Data accessibility: <evidence>
  - Handovers: <evidence>
  - External dependencies: <evidence>
  - **Why this rating overall**: <1–2 sentences>

- **Wave: <assignment>**
- **Notes / caveats**: <anything a partner should know before defending this>
```

Plus a section at the end on Wave 1 anchor selection.

This file is the audit trail. If a consultant gets challenged in a client meeting on "why is this Wave 1 and not Wave 2", `scoring_workings.md` is where the answer lives.
