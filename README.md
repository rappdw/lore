# lore

A host-side CLI that gives you **one lens over the memory your AI coding agents accumulate** — across projects *and* across agents (Claude Code, Gemini CLI, Codex, OpenCode). Explore it, search it, summarize it, find what applies elsewhere, and curate it.

> Status: **`0.2.0` built** — the read-only memory core + Claude adapter (`ls`/`search`/`show`/`graph`/`stats`/`export`), **deterministic session profiles** (`sessions`/`session`), the **memory↔session provenance bridge** (a memory shows the session it came from; a session lists the memories it produced; `stats`/`sessions` flag sessions that produced none), and the first **LLM features** — `summarize` (a digest of what's been learned) and `relevant <project>` (cross-project memories that may apply here), both opt-in via the Anthropic Messages API atop a deterministic token-overlap scorer. Next: curation (`0.3.0`), other agents (`0.4.0`). See [ROADMAP.md](ROADMAP.md) and [PLAN.md](PLAN.md).

## Why

Coding agents quietly accumulate memory — Claude Code's auto-memory, Gemini's `/memory`, Codex's memories, plus every project's `CLAUDE.md` / `GEMINI.md` / `AGENTS.md`. With [sandy](https://github.com/rappdw/sandy), each project's memory is isolated in its own sandbox — *no bleed between contexts*, by design. The cost of that isolation: everything your agents have learned ends up scattered across dozens of stores, in several formats, with no way to see it as a whole, spot duplication, or carry a hard-won lesson from one project to another.

`lore` is the deliberate complement: **isolation by default, one cross-agent lens on demand.** Every cross-context action (copying a memory into another project, merging duplicates) stays explicit — and where it would mutate, it's gated and reversible.

## What it reads

Per-agent **adapters** normalize each agent's memory into one model (details + caveats in [SPECIFICATION.md §3](SPECIFICATION.md)):

| Agent | What lore reads | Notes |
|---|---|---|
| **Claude Code** | `…/claude/projects/<repo>/memory/` (`MEMORY.md` + topic files) | richest — optional typed frontmatter + `[[links]]` |
| **Gemini CLI** | `…/gemini/GEMINI.md` (the `/memory` store) | markdown; exact target is version-dependent |
| **Codex** | `…/codex/memories/` | **read-only** — "generated state", never hand-edited |
| **OpenCode** | `AGENTS.md` instructions | no native memory store (core) |

The primary **source** is your **sandy sandboxes** (enumerated via `sandy --print-state`); reading host-native installs (`~/.claude`, `~/.gemini`, …) directly is a planned second source. v0 covers accumulated memory + (opt-in) context files — **not** raw session transcripts (deferred; see [ROADMAP.md](ROADMAP.md)).

## Commands

| Command | Does | Uses LLM | Mutates |
|---|---|:--:|:--:|
| `ls` / `list [--type --project --sort]` | memories per project, flat **A–Z by title** (type shown inline) | — | — |
| `search <query>` | match title / description / body across all sources | — | — |
| `show <title>` | a memory plus its `[[link]]` neighborhood | — | — |
| `graph [--dot]` | the wikilink graph (sparse for non-Claude agents) | — | — |
| `stats` | counts by agent/type/project, growth, orphan & dangling links | — | — |
| `export [--json \| --md]` | a consolidated digest | — | — |
| `sessions [--project P --sort …]` | list session transcripts: title, timing, msg/tool counts, branch | — | — |
| `session <id\|title>` | full profile of one session: tools, files touched, PRs, errors, opening prompt | — | — |
| `menu` | interactive picker — choose a command, get prompted for its options, then it runs | — | — |
| `summarize [--agent A --project P --type T --model M]` | "what have the agents learned?" digest, grouped by theme, map-reduced over a char budget | ✓ | — |
| `relevant <project> [--top N --explain --model M]` | memories from *other* projects/agents that may apply here; ranked offline, `--explain` adds LLM rationales | ✓ (only `--explain`) | — |
| `copy <title> --to <project>` | deliberately carry one memory into another sandbox | — | ✓ |
| `dedup` / `merge` / `prune` | find & resolve duplicate / stale / contradictory memories | opt-in | ✓ |

Read-only commands are the default surface and work offline. LLM commands call the Anthropic Messages API over stdlib HTTP — no SDK — authenticating with `ANTHROPIC_API_KEY` from the environment or `~/.sandy/.secrets`. Mutating commands default to `--dry-run`, require `--apply`, never touch Codex's generated state or a locked sandbox.

Flags follow the subcommand:

```sh
lore ls                              # everything, grouped by project/agent/type
lore search "egress proxy"           # ranked across all sources
lore show roadmap-1.0-position       # one memory + its [[links]]
lore stats --json                    # machine-readable counts/mismatches/dangling
lore summarize --project myapp       # LLM digest of what's been learned (needs ANTHROPIC_API_KEY)
lore relevant myapp                  # offline-ranked memories from elsewhere that may apply
lore relevant myapp --explain        # …plus LLM rationales for each
lore ls --sandboxes-root ~/.sandy/sandboxes   # explicit source (skips `sandy --print-state`)
```

## Requirements

- **Python 3.9+** — standard library only, no `pip install`.
- **A source of agent memory** — sandy sandboxes (`sandy` on `PATH`, for `--print-state` enumeration), or an explicit `--sandboxes-root`.
- **An `ANTHROPIC_API_KEY`** — in the environment or `~/.sandy/.secrets` — only for `summarize` / `relevant`. (A Claude Code subscription OAuth token is *not* usable — Anthropic prohibits routing it through third-party tools.) Everything else works offline.

## Design notes

- **Agent-agnostic via adapters** — new agents are new adapters; the core never assumes Claude's shape.
- **Read-only by default**; only curation mutates, dry-run-first and reversible.
- **Single file, zero dependencies** — like sandy. Self-contained: liftable into its own repo unchanged.

## Install

> Not yet published. Planned to mirror sandy: a single file installed to `~/.local/bin/` via `curl | bash`, or a local install from a clone. (Binary-name collision check pending — `lore` is a common word.)

## License

MIT.
