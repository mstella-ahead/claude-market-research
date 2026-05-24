"""
Blind LLM judge for the Claude-vs-Parallel external-research benchmark.

Calls Claude Opus 4.7 via the Anthropic SDK. The two provider outputs are
shown as Output A and Output B with random assignment; the mapping is logged
in judge_scores.json so a human can de-anonymise.

The judge is explicitly instructed NOT to trust the provider's self-tagged
citations.source_type. It independently classifies a sample of citations
based on URL patterns and reports any mismatches; these mismatches feed the
citation_quality score.

Loads .env at the repo root for ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
JUDGE_SCHEMA_PATH = REPO_ROOT / "bench" / "judge_schema.json"

JUDGE_MODEL = "claude-opus-4-7"

JUDGE_SYSTEM = """You are a senior research-quality reviewer scoring two outside-in company-research dossiers produced by different research systems. You will not know which system produced which output. Score them blind, on a 1-5 scale across five criteria, then deliver an overall verdict.

You MUST be skeptical. In particular: do NOT trust each output's self-classification of its citations (`source_type` = primary | secondary | aggregator). Instead, independently classify a sample of citations using URL patterns:

- **primary** = the company's own domain (company-name.com), official regulators (sec.gov, *.gov, ferc.gov, courts.gov, etc.), or court filings
- **secondary** = reputable journalism (reuters.com, wsj.com, nytimes.com, bloomberg.com, etc.) or named analyst firms (gartner.com, forrester.com, etc.)
- **aggregator** = wikipedia.org, listicles, content farms, content-mill aggregators, broad SEO sites, AI-summary sites, or anything that itself just summarizes other sources

If a citation claims `primary` but the URL points to Wikipedia, that is a clear over-claim. If a citation claims `primary` but the URL points to a Reuters article about the company, that is also an over-claim (it's secondary). Report each mismatch in `source_type_audit.<A|B>.mismatches` with the citation index, what the provider claimed, your judgment, and a one-line URL-pattern note. Sample at least 5 citations per output (or all of them if fewer than 5 exist) — record the count in `citations_sampled`. Over-claiming should pull the `citation_quality` score down.

Rubric (1 = poor, 5 = excellent):

1. **factual_accuracy** — claims supported by cited evidence; no hallucinated facts; numbers consistent across the document.
2. **citation_quality** — primary > secondary > aggregator. Freshness, accessibility, named publishers. Adjust DOWN for source_type over-claiming you caught.
3. **coverage_breadth** — how many of the schema's expected categories have substantive content (company_basics, scale_snapshot, operating_model_signals, tech_stack_signals, recent_strategic_moves, public_pain_points, competitive_landscape).
4. **recency** — how recent are the cited sources for time-sensitive fields (scale_snapshot.year, recent_strategic_moves dates). For a 2026 dossier, sources from 2024-2026 are good; 2019 sources for current revenue are bad.
5. **structural_fidelity** — JSON conforms to schema; citation_indices point to valid citations; appropriate use of "not_disclosed" rather than guessing; agreement between markdown and JSON twins.

Return your output as a single JSON object matching the schema you'll be given. Use `tie` for verdict when scores are within 1 point on most criteria. List the criteria where the two outputs are within 1 point in `close_calls` — these are flagged for human spot-check."""


USER_PROMPT_TEMPLATE = """Company: {company}

Below are two outside-in research dossiers produced by different systems. Both target the same JSON schema. Each is presented as: (1) a markdown render, then (2) the raw JSON.

The two outputs are presented to you blind: you do not know which system produced A and which produced B, and obvious provenance markers (`researcher`, `generated_at`, and the markdown header equivalents) have been redacted. Score on substance, not on stylistic tells.

Set `mapping` in your output to `{{"A": "unknown", "B": "unknown"}}` — the harness will overwrite it with the real de-anonymisation when persisting your scores.

Score them blind per the rubric. Spot-check `citations.source_type` against URL patterns and report any over-claims.

Return a single JSON object conforming to this schema:

```json
{judge_schema}
```

================================================================================
## OUTPUT A — markdown

```markdown
{a_md}
```

## OUTPUT A — JSON

```json
{a_json}
```

================================================================================
## OUTPUT B — markdown

```markdown
{b_md}
```

## OUTPUT B — JSON

```json
{b_json}
```

================================================================================

Now produce your scoring JSON. Output only the JSON object — no prose, no markdown fences."""


def _load_text(path: Path, cap: int = 200_000) -> str:
    """Read a file, capping length so we don't blow the judge's context window
    on enormous outputs (200k chars is generous for an Opus 4.7 1M ctx call)."""
    text = path.read_text()
    if len(text) > cap:
        return text[:cap] + f"\n\n... [truncated; full file is {len(text)} chars]"
    return text


def _redact_provenance(md_text: str, json_text: str) -> tuple[str, str]:
    """Strip the obvious provenance markers that would let the judge de-anonymise
    A vs B without doing any real evaluation: the `researcher` and `generated_at`
    fields in JSON, and the corresponding `Generated:` / `Researcher:` lines in
    markdown."""
    try:
        obj = json.loads(json_text)
        if isinstance(obj, dict):
            if "researcher" in obj:
                obj["researcher"] = "<redacted>"
            if "generated_at" in obj:
                obj["generated_at"] = "<redacted>"
        json_redacted = json.dumps(obj, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        json_redacted = json_text

    md_filtered_lines = [
        line
        for line in md_text.splitlines()
        if not line.startswith("Generated:") and not line.startswith("Researcher:")
    ]
    return "\n".join(md_filtered_lines), json_redacted


def judge_outputs(
    *,
    claude_md_path: Path,
    claude_json_path: Path,
    parallel_md_path: Path,
    parallel_json_path: Path,
    run_dir: Path,
    company: str,
) -> dict[str, Any]:
    """Run the blind judge and persist judge_scores.json. Returns the scores dict."""
    load_dotenv(REPO_ROOT / ".env")

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(f"anthropic SDK not installed: {e}") from e

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set (expected in .env at repo root)")

    # Random assignment: shuffle which provider becomes A vs B.
    rng = random.Random()
    if rng.random() < 0.5:
        a_provider, b_provider = "claude", "parallel"
        a_md_path, a_json_path = claude_md_path, claude_json_path
        b_md_path, b_json_path = parallel_md_path, parallel_json_path
    else:
        a_provider, b_provider = "parallel", "claude"
        a_md_path, a_json_path = parallel_md_path, parallel_json_path
        b_md_path, b_json_path = claude_md_path, claude_json_path

    mapping = {"A": a_provider, "B": b_provider}

    a_md_raw = _load_text(a_md_path)
    a_json_raw = _load_text(a_json_path)
    b_md_raw = _load_text(b_md_path)
    b_json_raw = _load_text(b_json_path)

    # Redact obvious provenance markers (researcher, generated_at, the markdown
    # header equivalents) so the judge can't trivially de-anonymise A vs B by
    # reading them. The harness keeps the real mapping and re-attaches it after
    # the judge returns.
    a_md, a_json = _redact_provenance(a_md_raw, a_json_raw)
    b_md, b_json = _redact_provenance(b_md_raw, b_json_raw)

    judge_schema = json.loads(JUDGE_SCHEMA_PATH.read_text())

    user_prompt = USER_PROMPT_TEMPLATE.format(
        company=company,
        judge_schema=json.dumps(judge_schema, indent=2),
        a_md=a_md,
        a_json=a_json,
        b_md=b_md,
        b_json=b_json,
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4096,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            raw_text += block.text

    # Persist raw judge response for audit.
    (run_dir / "judge_raw_response.txt").write_text(raw_text)

    # Parse JSON out of the response. Be tolerant of stray prose or fences.
    parsed = _extract_json(raw_text)
    if parsed is None:
        raise RuntimeError(f"Judge returned no parseable JSON. See {run_dir / 'judge_raw_response.txt'}")

    # Force the mapping to the one we generated (so any judge confusion can't
    # silently flip de-anonymisation).
    parsed["mapping"] = mapping

    out_path = run_dir / "judge_scores.json"
    out_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False))

    # Token / cost log for the judge call itself.
    usage = getattr(response, "usage", None)
    if usage is not None:
        (run_dir / "judge_usage.json").write_text(
            json.dumps(
                {
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                    "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                    "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
                    "model": JUDGE_MODEL,
                },
                indent=2,
            )
        )

    return parsed


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        # remove leading ``` (optionally with language tag) and trailing ```
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the outermost JSON object via brace matching.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
