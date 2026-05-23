#!/usr/bin/env python3
"""
Claude vs Parallel.ai external-research benchmark harness.

Runs both providers on the same target company, captures wall-clock latency,
token usage where available, and per-run cost, then dispatches a blind LLM
judge to score the two outputs. Writes everything to
`bench/results/<slug>-<utc_timestamp>/`.

Usage:
    python bench/run.py --company "American Electric Power"
    python bench/run.py --summary               # roll up all prior runs

Reads .env from the repo root for ANTHROPIC_API_KEY and PARALLEL_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = REPO_ROOT / "bench"
RESULTS_DIR = BENCH_DIR / "results"
CLAUDE_STAGING = RESULTS_DIR / "claude"            # where the slash command stages output
SCHEMA_PATH = BENCH_DIR / "schema.json"
PRICING_PATH = BENCH_DIR / "pricing.json"
COMPANIES_PATH = BENCH_DIR / "companies.yaml"

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ProviderResult:
    provider: str
    success: bool
    wall_time_sec: float
    error: str | None = None
    md_path: str | None = None
    json_path: str | None = None

    # Token / call accounting (best-effort)
    tokens_in: int | None = None
    tokens_out: int | None = None
    cache_read_tokens: int | None = None
    cache_write_5m_tokens: int | None = None
    cache_write_1h_tokens: int | None = None
    web_searches: int | None = None
    cost_usd: float | None = None
    usage_capture_note: str | None = None

    # Provider-specific
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_pricing() -> dict[str, Any]:
    with open(PRICING_PATH) as f:
        return json.load(f)


def load_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Claude path: shell out to `claude -p`
# ---------------------------------------------------------------------------


def run_claude(company: str, slug: str, run_dir: Path, pricing: dict[str, Any]) -> ProviderResult:
    """Invoke the bench-external slash command via `claude -p` and stage outputs."""

    # Clean the staging dir so we know any output we see is fresh.
    staging = CLAUDE_STAGING / slug
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    cmd = [
        "claude",
        "-p",
        f"/market-research:bench-external {company}",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",  # non-interactive: sub-agents need tool calls auto-approved
    ]

    # Scrub Anthropic auth vars from `claude -p`'s env. The harness loads
    # .env into os.environ so the judge's anthropic SDK can authenticate,
    # but `claude -p` is its own CLI signed into the user's Claude account
    # via OAuth. If it sees ANTHROPIC_API_KEY in its env it uses that key
    # instead — which is the API console key, not the OAuth credential —
    # and 401s.
    claude_env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "ANTHROPIC_AUTH_TOKEN"}
    }

    start = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60 * 60,  # 1 hour ceiling
            check=False,
            env=claude_env,
        )
    except FileNotFoundError as e:
        wall = time.monotonic() - start
        return ProviderResult(provider="claude", success=False, wall_time_sec=wall, error=f"claude CLI not found: {e}")
    except subprocess.TimeoutExpired:
        wall = time.monotonic() - start
        return ProviderResult(provider="claude", success=False, wall_time_sec=wall, error="claude -p timed out after 1h")
    wall = time.monotonic() - start

    # Persist raw CLI output for debugging
    (run_dir / "claude_cli_stdout.txt").write_text(completed.stdout)
    if completed.stderr:
        (run_dir / "claude_cli_stderr.txt").write_text(completed.stderr)

    if completed.returncode != 0:
        return ProviderResult(
            provider="claude",
            success=False,
            wall_time_sec=wall,
            error=f"claude -p exited with code {completed.returncode}. See claude_cli_stderr.txt.",
        )

    # Parse the final JSON result.
    cli_json: dict[str, Any] = {}
    try:
        cli_json = json.loads(completed.stdout)
    except json.JSONDecodeError:
        # The CLI may emit a stream of JSON lines depending on version. Try last line.
        for line in reversed(completed.stdout.strip().splitlines()):
            try:
                cli_json = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

    # Move the slash command's staged outputs into the run dir.
    src_md = staging / "external_report.md"
    src_json = staging / "external_report.json"
    if not src_md.exists() or not src_json.exists():
        return ProviderResult(
            provider="claude",
            success=False,
            wall_time_sec=wall,
            error=f"Expected staged outputs missing: md={src_md.exists()} json={src_json.exists()}",
        )

    dst_md = run_dir / "claude_output.md"
    dst_json = run_dir / "claude_output.json"
    shutil.copy2(src_md, dst_md)
    shutil.copy2(src_json, dst_json)

    # Extract usage from cli_json (defensive — exact fields vary by Claude Code version).
    usage = cli_json.get("usage", {}) if isinstance(cli_json, dict) else {}
    server_tool = usage.get("server_tool_use", {}) if isinstance(usage, dict) else {}
    capture_notes: list[str] = []

    tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    cache_read = usage.get("cache_read_input_tokens")
    cache_write_5m = usage.get("cache_creation_input_tokens")  # 5m write is the common case
    cache_write_1h = usage.get("cache_creation_1h_input_tokens")
    web_searches = server_tool.get("web_search_requests") if isinstance(server_tool, dict) else None

    if tokens_in is None and tokens_out is None:
        capture_notes.append(
            "claude -p --output-format json did not surface input/output tokens on the top-level response. "
            "Sub-agent usage may not be aggregated here. Consider parsing the session log if precise totals matter."
        )

    cost = cli_json.get("total_cost_usd")
    if cost is None:
        cost = compute_claude_cost(
            pricing,
            tokens_in=tokens_in or 0,
            tokens_out=tokens_out or 0,
            cache_read=cache_read or 0,
            cache_write_5m=cache_write_5m or 0,
            cache_write_1h=cache_write_1h or 0,
            web_searches=web_searches or 0,
        )
        if tokens_in is None or tokens_out is None:
            capture_notes.append("Cost computed from available usage fields only; treat as a lower bound.")

    return ProviderResult(
        provider="claude",
        success=True,
        wall_time_sec=wall,
        md_path=str(dst_md.relative_to(REPO_ROOT)),
        json_path=str(dst_json.relative_to(REPO_ROOT)),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cache_read_tokens=cache_read,
        cache_write_5m_tokens=cache_write_5m,
        cache_write_1h_tokens=cache_write_1h,
        web_searches=web_searches,
        cost_usd=cost,
        usage_capture_note="; ".join(capture_notes) if capture_notes else None,
        extra={
            "cli_session_id": cli_json.get("session_id"),
            "cli_num_turns": cli_json.get("num_turns"),
            "cli_duration_ms": cli_json.get("duration_ms"),
        },
    )


def compute_claude_cost(
    pricing: dict[str, Any],
    *,
    tokens_in: int,
    tokens_out: int,
    cache_read: int,
    cache_write_5m: int,
    cache_write_1h: int,
    web_searches: int,
) -> float:
    p = pricing["claude_opus_4_7"]
    per_mtok = 1_000_000
    total = 0.0
    total += (tokens_in / per_mtok) * p["input_per_mtok_usd"]
    total += (tokens_out / per_mtok) * p["output_per_mtok_usd"]
    total += (cache_read / per_mtok) * p["cache_read_per_mtok_usd"]
    total += (cache_write_5m / per_mtok) * p["cache_write_5m_per_mtok_usd"]
    total += (cache_write_1h / per_mtok) * p["cache_write_1h_per_mtok_usd"]
    total += (web_searches / 1000.0) * p["web_search_per_1k_searches_usd"]
    return round(total, 6)


# ---------------------------------------------------------------------------
# Parallel path: call the Task API
# ---------------------------------------------------------------------------

PARALLEL_INPUT_TEMPLATE = (
    "Research the company '{company}' for an outside-in consulting dossier. "
    "Cover operating model, scale, tech stack signals, recent strategic moves, "
    "pain points, and competitive landscape. Cite every non-trivial claim with "
    "a primary or reputable secondary source. For the citations array, mark each "
    "source's source_type honestly: primary = company itself or regulator/court; "
    "secondary = reputable journalism or analyst report; aggregator = listicle, "
    "Wikipedia, or content farm."
)


def run_parallel(company: str, slug: str, run_dir: Path, pricing: dict[str, Any]) -> ProviderResult:
    try:
        from parallel import Parallel
    except ImportError as e:
        return ProviderResult(
            provider="parallel",
            success=False,
            wall_time_sec=0.0,
            error=f"parallel-web SDK not installed: {e}",
        )

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return ProviderResult(
            provider="parallel",
            success=False,
            wall_time_sec=0.0,
            error="PARALLEL_API_KEY not set (expected in .env at repo root)",
        )

    schema = load_schema()
    client = Parallel(api_key=api_key)

    start = time.monotonic()
    try:
        task_run = client.task_run.create(
            input=PARALLEL_INPUT_TEMPLATE.format(company=company),
            processor="pro",
            task_spec={
                "output_schema": {
                    "json_schema": schema,
                    "type": "json",
                },
            },
        )
        run_result = client.task_run.result(task_run.run_id)
    except Exception as e:
        wall = time.monotonic() - start
        return ProviderResult(
            provider="parallel",
            success=False,
            wall_time_sec=wall,
            error=f"Parallel API call failed: {e!r}\n{traceback.format_exc()}",
        )
    wall = time.monotonic() - start

    content = getattr(run_result.output, "content", None)
    basis = getattr(run_result.output, "basis", None)

    if content is None:
        return ProviderResult(
            provider="parallel",
            success=False,
            wall_time_sec=wall,
            error="Parallel returned no result.output.content",
        )

    # Ensure content is a dict — SDK may already give us a parsed object.
    if isinstance(content, str):
        try:
            content_obj = json.loads(content)
        except json.JSONDecodeError as e:
            return ProviderResult(
                provider="parallel",
                success=False,
                wall_time_sec=wall,
                error=f"Parallel returned non-JSON content: {e}",
            )
    else:
        content_obj = content

    json_path = run_dir / "parallel_output.json"
    json_path.write_text(json.dumps(content_obj, indent=2, ensure_ascii=False))

    md_path = run_dir / "parallel_output.md"
    md_path.write_text(render_md(content_obj))

    # Save the basis array separately for the judge.
    if basis is not None:
        try:
            basis_serialisable = (
                basis if isinstance(basis, (dict, list)) else json.loads(json.dumps(basis, default=str))
            )
            (run_dir / "parallel_basis.json").write_text(
                json.dumps(basis_serialisable, indent=2, ensure_ascii=False, default=str)
            )
        except Exception:  # noqa: BLE001
            (run_dir / "parallel_basis.json").write_text(str(basis))

    cost = pricing["parallel_task"]["pro_per_task_run_usd"]

    return ProviderResult(
        provider="parallel",
        success=True,
        wall_time_sec=wall,
        md_path=str(md_path.relative_to(REPO_ROOT)),
        json_path=str(json_path.relative_to(REPO_ROOT)),
        cost_usd=cost,
        usage_capture_note="Parallel pro is per-task pricing; no per-token meter applies.",
        extra={
            "run_id": getattr(task_run, "run_id", None),
            "processor": "pro",
        },
    )


# ---------------------------------------------------------------------------
# render_md: deterministic JSON -> markdown for the Parallel output
# ---------------------------------------------------------------------------


def render_md(report: dict[str, Any]) -> str:
    """Render an ExternalResearchReport JSON object to markdown that mirrors the
    schema of external_report.md (so it's directly comparable to the Claude path)."""

    def cite(indices: list[int] | None) -> str:
        if not indices:
            return ""
        return " " + ", ".join(f"[^{i}]" for i in indices)

    def safe(d: dict | None, key: str, default: Any = "") -> Any:
        if not isinstance(d, dict):
            return default
        return d.get(key, default)

    out: list[str] = []
    out.append(f"# External Research: {report.get('company', '')}")
    out.append(f"Generated: {report.get('generated_at', '')}")
    out.append(f"Researcher: {report.get('researcher', '')}")
    out.append("")

    # TL;DR
    out.append("## TL;DR")
    for bullet in report.get("tldr", []) or []:
        if isinstance(bullet, dict):
            out.append(f"- {bullet.get('bullet', '')}{cite(bullet.get('citation_indices'))}")
    out.append("")

    # What they do
    basics = report.get("company_basics", {}) or {}
    out.append("## What they do")
    summary = basics.get("summary", {}) or {}
    out.append(f"{safe(summary, 'text')}{cite(safe(summary, 'citation_indices', []))}")
    out.append("")

    if basics.get("products_services"):
        out.append("### Products & services")
        for p in basics["products_services"]:
            out.append(f"- **{p.get('name', '')}** — {p.get('description', '')}{cite(p.get('citation_indices'))}")
        out.append("")

    if basics.get("customer_segments"):
        out.append("### Customer segments")
        for s in basics["customer_segments"]:
            out.append(f"- {s.get('segment', '')}{cite(s.get('citation_indices'))}")
        out.append("")

    bm = basics.get("business_model", {}) or {}
    if bm.get("text"):
        out.append("### Business model")
        out.append(f"{bm.get('text', '')}{cite(bm.get('citation_indices'))}")
        out.append("")

    # Scale snapshot
    out.append("## Scale snapshot")
    scale = report.get("scale_snapshot", {}) or {}
    for label, key in [("Revenue", "revenue"), ("Employees", "employees"), ("Customers", "customers")]:
        f = scale.get(key, {}) or {}
        year = f.get("year", "")
        out.append(
            f"- **{label}**: {f.get('value', '')}"
            + (f" ({year})" if year else "")
            + f" — confidence: {f.get('confidence', '')}"
            + cite(f.get("citation_indices"))
        )
    geo = scale.get("geography", {}) or {}
    out.append(f"- **Geography**: {geo.get('value', '')} — confidence: {geo.get('confidence', '')}{cite(geo.get('citation_indices'))}")
    out.append("")

    # Operating model
    out.append("## Operating model (outside-in)")
    for s in report.get("operating_model_signals", []) or []:
        out.append(
            f"- **{s.get('function', '')}** [{s.get('evidence_type', '')}]: {s.get('signal', '')} "
            f"(confidence: {s.get('confidence', '')}){cite(s.get('citation_indices'))}"
        )
    out.append("")

    # Tech stack
    out.append("## Tech stack signal")
    for s in report.get("tech_stack_signals", []) or []:
        out.append(
            f"- **{s.get('system', '')}** ({s.get('category', '')}) "
            f"[{s.get('evidence_type', '')}, confidence: {s.get('confidence', '')}]{cite(s.get('citation_indices'))}"
        )
    out.append("")

    # Recent moves
    out.append("## Recent strategic moves (last 12-18 months)")
    for m in report.get("recent_strategic_moves", []) or []:
        out.append(f"- **{m.get('date', '')}** [{m.get('category', '')}]: {m.get('event', '')}{cite(m.get('citation_indices'))}")
    out.append("")

    # Pain points
    out.append("## Public pain points / criticisms")
    for p in report.get("public_pain_points", []) or []:
        out.append(f"### {p.get('theme', '')} — *{p.get('prevalence', '')}*")
        out.append(f"Source pattern: {p.get('source_pattern', '')}{cite(p.get('citation_indices'))}")
        for q in p.get("representative_quotes", []) or []:
            ci = q.get("citation_index")
            ci_str = f" [^{ci}]" if ci is not None else ""
            out.append(f"> {q.get('quote', '')}{ci_str}")
        out.append("")

    # Competitive landscape
    out.append("## Competitive landscape")
    landscape = report.get("competitive_landscape", {}) or {}
    out.append("### Direct competitors")
    for c in landscape.get("direct_competitors", []) or []:
        out.append(f"- **{c.get('name', '')}** — {c.get('rationale', '')}{cite(c.get('citation_indices'))}")
    out.append("")
    out.append("### Adjacent threats")
    for c in landscape.get("adjacent_threats", []) or []:
        out.append(f"- **{c.get('name', '')}** — {c.get('rationale', '')}{cite(c.get('citation_indices'))}")
    out.append("")

    # Open questions
    out.append("## Open questions for the consolidator")
    for q in report.get("open_questions", []) or []:
        out.append(f"- {q}")
    out.append("")

    # Citations
    out.append("## Citations")
    for c in report.get("citations", []) or []:
        idx = c.get("id")
        sd = c.get("source_date") or "n/a"
        out.append(
            f"[^{idx}]: **{c.get('title', '')}** — {c.get('publisher', '')} ({sd}) "
            f"[{c.get('source_type', '')}] {c.get('url', '')} "
            f"(accessed {c.get('date_accessed', '')})"
        )

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Metrics & comparison
# ---------------------------------------------------------------------------


def write_metrics(run_dir: Path, claude_r: ProviderResult, parallel_r: ProviderResult) -> Path:
    metrics = {
        "company_slug": run_dir.name,
        "claude": asdict(claude_r),
        "parallel": asdict(parallel_r),
    }
    path = run_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
    return path


def fmt_cost(c: float | None) -> str:
    return f"${c:.4f}" if c is not None else "n/a"


def fmt_time(t: float | None) -> str:
    return f"{t:.1f}s" if t is not None else "n/a"


def generate_comparison_md(
    run_dir: Path,
    company: str,
    claude_r: ProviderResult,
    parallel_r: ProviderResult,
    judge: dict[str, Any] | None,
) -> Path:
    lines: list[str] = []
    lines.append(f"# Benchmark comparison: {company}")
    lines.append(f"_Run: `{run_dir.name}`_")
    lines.append("")

    lines.append("## Latency & cost")
    lines.append("")
    lines.append("| Provider | Success | Wall time | Cost (USD) | Tokens in | Tokens out | Web searches |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in (claude_r, parallel_r):
        lines.append(
            f"| {r.provider} | {'yes' if r.success else 'NO'} | {fmt_time(r.wall_time_sec)} | "
            f"{fmt_cost(r.cost_usd)} | {r.tokens_in if r.tokens_in is not None else 'n/a'} | "
            f"{r.tokens_out if r.tokens_out is not None else 'n/a'} | "
            f"{r.web_searches if r.web_searches is not None else 'n/a'} |"
        )
    lines.append("")

    if claude_r.error:
        lines.append(f"**Claude error:** {claude_r.error}")
        lines.append("")
    if parallel_r.error:
        lines.append(f"**Parallel error:** {parallel_r.error}")
        lines.append("")

    if claude_r.usage_capture_note:
        lines.append(f"_Claude usage note:_ {claude_r.usage_capture_note}")
        lines.append("")
    if parallel_r.usage_capture_note:
        lines.append(f"_Parallel usage note:_ {parallel_r.usage_capture_note}")
        lines.append("")

    # Outputs
    lines.append("## Outputs")
    lines.append(f"- Claude markdown: `{claude_r.md_path or 'n/a'}`")
    lines.append(f"- Claude JSON: `{claude_r.json_path or 'n/a'}`")
    lines.append(f"- Parallel markdown: `{parallel_r.md_path or 'n/a'}`")
    lines.append(f"- Parallel JSON: `{parallel_r.json_path or 'n/a'}`")
    lines.append("")

    # Judge scores
    if judge:
        lines.append("## Blind judge scores")
        lines.append("")
        mapping = judge.get("mapping", {})
        lines.append(f"_A = {mapping.get('A', '?')}, B = {mapping.get('B', '?')}_")
        lines.append("")
        lines.append("| Criterion | A score | B score | Notes |")
        lines.append("|---|---|---|---|")
        criteria = ["factual_accuracy", "citation_quality", "coverage_breadth", "recency", "structural_fidelity"]
        for crit in criteria:
            a = judge.get("per_output_scores", {}).get("A", {}).get(crit, {})
            b = judge.get("per_output_scores", {}).get("B", {}).get(crit, {})
            close = " **(close call)**" if crit in (judge.get("close_calls") or []) else ""
            lines.append(f"| {crit}{close} | {a.get('score', '?')} | {b.get('score', '?')} | |")
        lines.append("")
        lines.append(f"**Verdict:** {judge.get('verdict', '?')}")
        lines.append("")
        lines.append(f"_{judge.get('verdict_reasoning', '')}_")
        lines.append("")

        # Source-type audit
        sta = judge.get("source_type_audit")
        if sta:
            lines.append("### Source-type audit")
            for key in ("A", "B"):
                audit = sta.get(key, {})
                lines.append(
                    f"- **{key} ({mapping.get(key, '?')})**: sampled {audit.get('citations_sampled', 0)} citations, "
                    f"{len(audit.get('mismatches', []) or [])} mismatch(es)"
                )
                for m in audit.get("mismatches", []) or []:
                    lines.append(
                        f"  - citation #{m.get('citation_index')}: claimed `{m.get('claimed')}`, "
                        f"judged `{m.get('judged')}` — {m.get('url_pattern_evidence', '')}"
                    )
            lines.append("")

        # Close calls section for human spot-check
        close_calls = judge.get("close_calls") or []
        if close_calls:
            lines.append("### Close calls (human spot-check)")
            lines.append("")
            for crit in close_calls:
                a_r = judge.get("per_output_scores", {}).get("A", {}).get(crit, {})
                b_r = judge.get("per_output_scores", {}).get("B", {}).get(crit, {})
                lines.append(f"- **{crit}** — A: \"{a_r.get('reasoning', '')}\"  B: \"{b_r.get('reasoning', '')}\"")
            lines.append("")
    else:
        lines.append("## Blind judge scores")
        lines.append("_Judge did not run (no successful outputs to score, or judge error)._")
        lines.append("")

    path = run_dir / "comparison.md"
    path.write_text("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Per-company orchestration
# ---------------------------------------------------------------------------


def run_company(company: str) -> Path:
    pricing = load_pricing()
    slug = slugify(company)
    run_dir = RESULTS_DIR / f"{slug}-{utc_timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[bench] company={company!r} slug={slug} run_dir={run_dir.relative_to(REPO_ROOT)}")

    # Claude path
    print("[bench] dispatching Claude path...")
    claude_r = run_claude(company, slug, run_dir, pricing)
    print(f"[bench] claude: success={claude_r.success} wall={fmt_time(claude_r.wall_time_sec)} cost={fmt_cost(claude_r.cost_usd)}")
    if claude_r.error:
        print(f"[bench] claude error: {claude_r.error}")

    # Parallel path
    print("[bench] dispatching Parallel path (processor=pro, blocking)...")
    parallel_r = run_parallel(company, slug, run_dir, pricing)
    print(f"[bench] parallel: success={parallel_r.success} wall={fmt_time(parallel_r.wall_time_sec)} cost={fmt_cost(parallel_r.cost_usd)}")
    if parallel_r.error:
        print(f"[bench] parallel error: {parallel_r.error}")

    # Metrics
    write_metrics(run_dir, claude_r, parallel_r)

    # Judge — only if both produced outputs
    judge_scores: dict[str, Any] | None = None
    if claude_r.success and parallel_r.success:
        from judge import judge_outputs  # local import to keep startup fast

        print("[bench] running blind judge...")
        try:
            judge_scores = judge_outputs(
                claude_md_path=Path(claude_r.md_path),
                claude_json_path=Path(claude_r.json_path),
                parallel_md_path=Path(parallel_r.md_path),
                parallel_json_path=Path(parallel_r.json_path),
                run_dir=run_dir,
                company=company,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[bench] judge failed: {e}")
            (run_dir / "judge_error.txt").write_text(f"{e}\n{traceback.format_exc()}")
    else:
        print("[bench] skipping judge — one or both providers failed")

    # Comparison artifact
    comparison_path = generate_comparison_md(run_dir, company, claude_r, parallel_r, judge_scores)
    print(f"[bench] wrote {comparison_path.relative_to(REPO_ROOT)}")

    return run_dir


# ---------------------------------------------------------------------------
# Summary across runs
# ---------------------------------------------------------------------------


def summary_rollup() -> None:
    run_dirs = sorted([d for d in RESULTS_DIR.glob("*-*Z") if d.is_dir() and (d / "metrics.json").exists()])
    if not run_dirs:
        print("[bench] no per-run results found")
        return

    lines: list[str] = []
    ts = utc_timestamp()
    lines.append(f"# Benchmark roll-up — {ts}")
    lines.append("")
    lines.append(f"_{len(run_dirs)} runs aggregated._")
    lines.append("")
    lines.append("| Run | Claude time | Claude $ | Parallel time | Parallel $ | Verdict |")
    lines.append("|---|---|---|---|---|---|")

    crit_totals = {
        "factual_accuracy": {"A": 0, "B": 0, "n": 0},
        "citation_quality": {"A": 0, "B": 0, "n": 0},
        "coverage_breadth": {"A": 0, "B": 0, "n": 0},
        "recency": {"A": 0, "B": 0, "n": 0},
        "structural_fidelity": {"A": 0, "B": 0, "n": 0},
    }
    # In rollup, normalize scores back to provider (not A/B) using mapping
    provider_crit = {
        p: {c: {"sum": 0.0, "n": 0} for c in crit_totals}
        for p in ("claude", "parallel")
    }
    total_time = {"claude": 0.0, "parallel": 0.0}
    total_cost = {"claude": 0.0, "parallel": 0.0}

    for d in run_dirs:
        metrics = json.loads((d / "metrics.json").read_text())
        c, p = metrics["claude"], metrics["parallel"]
        verdict = "—"
        judge_path = d / "judge_scores.json"
        if judge_path.exists():
            j = json.loads(judge_path.read_text())
            mapping = j.get("mapping", {})
            verdict_raw = j.get("verdict", "?")
            if verdict_raw in ("A_better", "B_better"):
                winner_letter = verdict_raw[0]
                verdict = f"{mapping.get(winner_letter, '?')} wins"
            else:
                verdict = "tie"
            # Aggregate per-provider scores
            for letter in ("A", "B"):
                prov = mapping.get(letter)
                if prov in provider_crit:
                    for crit in crit_totals:
                        s = j.get("per_output_scores", {}).get(letter, {}).get(crit, {}).get("score")
                        if isinstance(s, (int, float)):
                            provider_crit[prov][crit]["sum"] += s
                            provider_crit[prov][crit]["n"] += 1

        for prov, m in (("claude", c), ("parallel", p)):
            if m.get("wall_time_sec") is not None:
                total_time[prov] += m["wall_time_sec"]
            if m.get("cost_usd") is not None:
                total_cost[prov] += m["cost_usd"]

        lines.append(
            f"| {d.name} | {fmt_time(c.get('wall_time_sec'))} | {fmt_cost(c.get('cost_usd'))} "
            f"| {fmt_time(p.get('wall_time_sec'))} | {fmt_cost(p.get('cost_usd'))} | {verdict} |"
        )

    lines.append("")
    lines.append("## Totals")
    for prov in ("claude", "parallel"):
        lines.append(f"- **{prov}**: total time {fmt_time(total_time[prov])}, total cost {fmt_cost(total_cost[prov])}")
    lines.append("")

    lines.append("## Per-criterion average score (1-5)")
    lines.append("")
    lines.append("| Criterion | Claude avg | Parallel avg |")
    lines.append("|---|---|---|")
    for crit in crit_totals:
        c_avg = provider_crit["claude"][crit]
        p_avg = provider_crit["parallel"][crit]
        ca = f"{c_avg['sum']/c_avg['n']:.2f}" if c_avg["n"] else "n/a"
        pa = f"{p_avg['sum']/p_avg['n']:.2f}" if p_avg["n"] else "n/a"
        lines.append(f"| {crit} | {ca} | {pa} |")
    lines.append("")

    out_path = RESULTS_DIR / f"summary-{ts}.md"
    out_path.write_text("\n".join(lines))
    print(f"[bench] wrote {out_path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def judge_only(run_dir: Path) -> int:
    """Re-run the blind judge on an existing run dir without re-invoking either
    provider. Useful when the judge step failed (e.g., bad API key) but the
    provider outputs are intact."""

    if not run_dir.exists() or not (run_dir / "metrics.json").exists():
        print(f"error: {run_dir} is not a valid run dir (missing metrics.json)", file=sys.stderr)
        return 2

    metrics = json.loads((run_dir / "metrics.json").read_text())
    company = metrics.get("company_slug", run_dir.name).replace("-", " ").title()
    claude_md = run_dir / "claude_output.md"
    claude_json = run_dir / "claude_output.json"
    parallel_md = run_dir / "parallel_output.md"
    parallel_json = run_dir / "parallel_output.json"

    missing = [p for p in (claude_md, claude_json, parallel_md, parallel_json) if not p.exists()]
    if missing:
        print(f"error: required output files missing: {missing}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(BENCH_DIR))
    from judge import judge_outputs  # noqa: E402

    print(f"[bench] re-running judge on {run_dir.relative_to(REPO_ROOT)}")
    judge_scores = judge_outputs(
        claude_md_path=claude_md,
        claude_json_path=claude_json,
        parallel_md_path=parallel_md,
        parallel_json_path=parallel_json,
        run_dir=run_dir,
        company=company,
    )

    # Rebuild comparison.md from existing metrics + new judge scores.
    from dataclasses import fields as _fields
    claude_r = ProviderResult(**{k: metrics["claude"].get(k) for k in (f.name for f in _fields(ProviderResult)) if k in metrics["claude"]})
    parallel_r = ProviderResult(**{k: metrics["parallel"].get(k) for k in (f.name for f in _fields(ProviderResult)) if k in metrics["parallel"]})
    comparison_path = generate_comparison_md(run_dir, company, claude_r, parallel_r, judge_scores)
    print(f"[bench] wrote {comparison_path.relative_to(REPO_ROOT)}")

    # Clear judge_error.txt if it exists from a prior failed attempt.
    err_path = run_dir / "judge_error.txt"
    if err_path.exists():
        err_path.unlink()

    return 0


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")

    p = argparse.ArgumentParser()
    p.add_argument("--company", help="Canonical company name to research")
    p.add_argument("--summary", action="store_true", help="Roll up all prior runs into a summary markdown file")
    p.add_argument("--judge-only", help="Path to an existing run dir; re-run only the judge step on it")
    args = p.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.judge_only:
        return judge_only(Path(args.judge_only).resolve())

    if args.summary:
        summary_rollup()
        return 0

    if not args.company:
        print("error: --company is required (or pass --summary or --judge-only)", file=sys.stderr)
        return 2

    # Make bench/ importable for the judge module.
    sys.path.insert(0, str(BENCH_DIR))

    run_dir = run_company(args.company)
    print(f"[bench] done. comparison: {run_dir.relative_to(REPO_ROOT) / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
