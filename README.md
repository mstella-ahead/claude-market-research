# claude-market-research

A Claude Cowork plugin that runs **parallel internal (Glean) and external (web) market research** on a target company and auto-generates a **19-slide AI strategy proposal deck** in PowerPoint.

The plugin enforces strict isolation between the internal and external research streams (each runs in its own sub-agent with non-overlapping tools), then reconciles findings into a structured brief, then turns that brief into a deck.

## Why this exists

Single-thread research causes anchoring bias — whichever source the agent looks at first colors the rest. Two parallel, isolated researchers, reconciled by a third agent that flags conflicts rather than silently resolving them, produces a much more defensible dossier.

## Architecture

```
            [Input: Company Name]
                       │
                       ▼
                ┌──────────────┐
                │ /market-     │
                │  research:   │
                │  run         │
                └──────┬───────┘
                       │  (parallel dispatch via Task tool)
          ┌────────────┴────────────┐
          ▼                         ▼
  ┌──────────────────┐    ┌──────────────────┐
  │ internal-        │    │ external-        │
  │  researcher      │    │  researcher      │
  │ (Glean MCP only) │    │ (Web tools only) │
  └─────────┬────────┘    └─────────┬────────┘
            │                       │
            ▼                       ▼
   internal_report.md       external_report.md
            │                       │
            └───────────┬───────────┘
                        ▼
              ┌──────────────────┐
              │  consolidator    │
              │  (reconciles,    │
              │   flags          │
              │   conflicts)     │
              └─────────┬────────┘
                        ▼
            consolidated_brief.json
                        │
                        ▼  (human review of flagged conflicts)
                        │
                        ▼
              ┌──────────────────┐
              │  strategy-deck   │
              │  skill           │
              │  (scoring + 19-  │
              │   slide build)   │
              └─────────┬────────┘
                        ▼
                proposal.pptx
              + scoring_workings.md
```

## Prerequisites

- **Claude Cowork** (Claude Desktop on macOS or Windows, paid plan: Pro / Max / Team / Enterprise), or **Claude Code** (the CLI)
- **Glean MCP server** connected and named `glean_default` (one-time setup — see installation below). Without it, the plugin works external-only with the internal context flagged as missing.

## Installation

### 1. Fork or copy this repo to your own GitHub

Edit two files first to replace placeholders:

- `.claude-plugin/marketplace.json` → replace `Miltos Stella` and `mstella-ahead`
- `plugins/market-research/.claude-plugin/plugin.json` → same

### 2. Connect the Glean MCP server

The `internal-researcher` sub-agent reaches internal knowledge through a Glean MCP server. **It must be named exactly `glean_default`** — the agent's tools are namespaced `mcp__glean_default__*`, so any other name leaves the internal research stream empty.

**Claude Code (CLI)** — sub-agents run locally, so Glean is directly reachable:

```bash
claude mcp add glean_default https://<your-company>-be.glean.com/mcp/default --transport http --scope user
```

Then run `/mcp` and complete the OAuth sign-in.

**Cowork** — Claude Desktop → **Cowork** tab → **Customize** → **Connectors** → add a Glean **Web** connector. A local stdio Glean server (e.g. one defined in `claude_desktop_config.json`) is *not* reachable from Cowork's cloud research sandbox; it must be a Web connector, which your Glean/Cowork admin may need to provision.

For either path:

- Endpoint URL: ask your Glean admin (typically `https://<your-company>-be.glean.com/mcp/default` or similar)
- Auth: OAuth via your company's SSO (your admin may need to enable the Glean OAuth Authorization Server first)
- Required scopes: `MCP, AGENT, SEARCH, CHAT, DOCUMENTS, TOOLS, ENTITIES`

### 3. Add this marketplace to Cowork

Two ways:

**Via the Cowork UI** (easiest):
1. Cowork tab → Customize → **Plugins** → **Add marketplace**
2. Paste your GitHub repo URL (e.g., `https://github.com/<your-handle>/claude-market-research`)
3. Confirm

**Via the Claude CLI** (if you also use Claude Code):
```bash
claude plugin marketplace add <your-handle>/claude-market-research
claude plugin install market-research@market-research
```

### 4. Mount a working folder in Cowork

In Cowork, mount a folder where outputs should land — e.g., `~/Documents/client-research/`. The plugin will create `runs/<company-slug>/` inside it.

### 5. Test

In Cowork, type:

```
/market-research:run Acme Benefits Inc
```

You should see Cowork plan the work, spawn two parallel sub-agents (visible as side panels), then the consolidator, then ask you to review any flagged conflicts before generating the deck.

## What you get

After a successful run, `./runs/<company-slug>/` contains:

| File | What it is |
|---|---|
| `internal_report.md` | Glean-only findings about the company |
| `external_report.md` | Web-only findings about the company |
| `consolidated_brief.json` | Reconciled brief with conflicts flagged |
| `scoring_workings.md` | Audit trail of impact/readiness scoring and wave assignments |
| `proposal.pptx` | The 19-slide deck |

Always review `scoring_workings.md` before sending the deck — it's how you defend the wave assignments if a client challenges them.

## Customizing for your team

This plugin ships with reasonable defaults but the real value comes from tailoring it to your firm. The highest-leverage edits:

- **`skills/strategy-deck/references/slide_blueprints.md`** — adjust slide titles to match your firm's voice, add your branding requirements, swap example titles for ones from your past decks.
- **`skills/strategy-deck/references/scoring_rubric.md`** — encode your firm's POV on what "high impact" actually means in your sectors.
- **`agents/internal-researcher.md`** — add domain-specific search queries your senior consultants would run. The more your firm's institutional knowledge is encoded here, the better the internal report.
- **`agents/external-researcher.md`** — add your firm's preferred primary sources (specific industry analysts, trade publications).

Plugin updates flow to your team automatically when you push to the main branch and they run `/plugin marketplace update`.

## File structure

```
claude-market-research/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── market-research/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── README.md
│       ├── commands/
│       │   └── run.md
│       ├── agents/
│       │   ├── internal-researcher.md
│       │   ├── external-researcher.md
│       │   └── consolidator.md
│       └── skills/
│           ├── company-research/
│           │   └── SKILL.md
│           └── strategy-deck/
│               ├── SKILL.md
│               └── references/
│                   ├── slide_blueprints.md
│                   └── scoring_rubric.md
├── README.md
├── LICENSE
└── .gitignore
```

## Troubleshooting

**"Glean tools not available"** — The Glean MCP server isn't set up, or it isn't named `glean_default` (the `internal-researcher` agent's tools are namespaced to that exact name). See Installation step 2; verify the connection with `/mcp` in Claude Code or the Connectors panel in Cowork. You can still run external-only by telling the agent to proceed; it will clearly flag the missing internal context in the brief.

**"Both researchers returned almost nothing"** — Often means the company name is ambiguous (e.g., a holdco vs. subsidiary, name collision with a more famous entity). Re-run with a more specific name, e.g., `/market-research:run Acme Health Benefits LLC (subsidiary of Acme Corp)`.

**"The consolidator silently dropped conflicting facts"** — It shouldn't. If you see this, the agent isn't following the rubric. Check `internal_report.md` and `external_report.md` directly and re-run the consolidator with an explicit reminder to flag conflicts in `conflicts_for_human_review`.

**"Deck looks generic on slides 5–8"** — Those are intentionally generic (methodology). Customize them once in `slide_blueprints.md` to match your firm's voice; future runs will use the new template.

## License

MIT — see [LICENSE](./LICENSE).

## Contributing

This is a starter scaffold. The biggest opportunities for contributions are sector-specific scoring rubric variants (e.g., `references/scoring_rubric_healthcare.md`, `_fintech.md`) and richer slide blueprints.
