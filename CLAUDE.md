# CLAUDE.md — lore

Guidance for Claude Code when working in this repository (`lore` — a standalone, self-contained tool).

## What this is

`lore` is a single-file, standard-library-only **Python 3** CLI that reads the persistent memory + context AI coding agents accumulate (Claude Code, Gemini CLI, Codex, OpenCode), normalizes it across agents into one model, and lets the user explore / summarize / relate / export / curate it.

It is **agent-agnostic** and **source-agnostic** — built around per-agent *adapters* and a normalized record, not around any one agent's shape. The primary source is sandy sandboxes (via `sandy --print-state`), but lore depends only on sandy's published *introspection contract* (`sandy --print-schema` / `--print-state`), never its internals — so it ships and versions independently.

## Core invariants (do not regress)

1. **Single file, stdlib only.** No third-party deps, no `pip install`. Mirrors sandy's single-file / zero-dependency / `curl | bash` ethos.
2. **The core model is plain markdown; frontmatter is optional enrichment.** Claude's documented memory format is `MEMORY.md` + plain-markdown topic files. The `name`/`description`/`type` frontmatter is what *this* harness happens to write — parse it when present (hand-parse the constrained subset; no PyYAML), but **never require it**, and never assume other agents have it.
3. **Agent-agnostic via adapters.** Each adapter (SPEC §3) maps one agent's on-disk memory/context to the normalized `MemoryItem` (SPEC §4). Adapters **degrade gracefully and never hard-fail on an unexpected layout** — these formats are version-dependent (Codex especially is "generated state" with an uncontracted layout).
4. **Read-only by default.** Only `dedup` / `merge` / `prune` / `copy` mutate, and only with `--apply`. Everything else is a pure read and works with no network.
5. **Mutation safety** (SPEC §7): `--dry-run` default (unified diff); `--apply` to write; back up every changed file to `$SANDY_HOME/lore-backups/<UTC>/…` first; rewrite the `MEMORY.md` index line on `merge`/`prune`; **refuse a sandbox with `lock_holder_alive: true`**; and **never mutate a `readonly` adapter item (Codex `memories/`)** — point the user at `AGENTS.md` instead.
6. **LLM is opt-in and auth-free.** `summarize` / `relevant` shell out to `claude -p` (reusing the user's auth). The read-only core MUST work without `claude` on `PATH` and without network. Never require an API key.
7. **Enumerate via the contract.** Discover sandboxes by parsing `sandy --print-state`; fall back to walking `$SANDY_HOME/sandboxes/`. Don't duplicate sandy's sandbox-layout logic — consume its JSON.
8. **Transcripts (sessions) are a separate surface, streamed and tolerant.** Session profiles (`sessions`/`session`) read `<sandbox>/claude/projects/<slug>/*.jsonl` — large files with an undocumented, version-stamped JSONL schema. `scan_session` MUST **stream line-by-line** (never load whole), skip a bad/truncated line, and never hard-fail on an unknown event type. Keep sessions OUT of the memory model (`MemoryItem`) — they have their own `SessionProfile` and commands, so the high-signal memory view stays clean. Claude-only for now.

## Where memory lives (summary; authoritative table in SPEC §3)

- **claude** — `<src>/claude/projects/<repo>/memory/` (`MEMORY.md` + topic `*.md`). High reliability. Mutable under §7.
- **gemini** — `<src>/gemini/GEMINI.md` (the `/memory` append store). Treat as one document. Exact target version-dependent.
- **codex** — `<src>/codex/memories/`. **Read-only.** Tolerate format drift; never edit.
- **opencode** — instruction files (`AGENTS.md`) only in core; no native memory store. No plugin paths assumed.

Project instruction files (`CLAUDE.md`/`GEMINI.md`/`AGENTS.md`) live in the **workspace**, not the agent state dir, and are opt-in (`--include-instructions`).

## Testing

lore runs **host-side** — it needs the sandbox/host state dirs, not mounted into a sandy container. Inside sandy you can see only the current sandbox's own Claude memory, so:

- Build & unit-test against **synthetic fixtures** (a temp dir of fake sandboxes with per-agent state trees) via `--sandboxes-root <dir>`. Include all four agents' shapes, malformed/frontmatter-less files, a dangling link, an index/file mismatch.
- Validate the real multi-sandbox + LLM paths **on the host** (same constraint as sandy's own suites).

Stdlib `unittest`; runnable via `tests/run.sh` (which also runs `python3 -m py_compile lore`). No pytest dependency.

## Keep docs in sync

**SPECIFICATION.md** is the contract — update it with any behavior change. **README.md** is user-facing; **PLAN.md** / **ROADMAP.md** track build state and direction.

## Build order

`v0a` core + Claude adapter (read-only) → `v0b` Gemini/Codex/OpenCode adapters (read-only) → `v0c` LLM (`summarize`/`relevant`) → `v0d` curation. Don't start a later increment before the earlier one is tested. See [PLAN.md](PLAN.md).
