# lore — Specification

Version: draft (pre-0.1.0). The contract `lore` implements. Keep it in lockstep with the code.

`lore` is a single-file, stdlib-only Python 3 CLI that reads the persistent memory and context AI coding agents accumulate, normalizes it across agents into one model, and lets you explore, summarize, relate, export, and (carefully) curate it.

---

## 1. Scope

- **Agent-agnostic.** Claude Code, Gemini CLI, OpenAI Codex CLI, and OpenCode, via per-agent **adapters** (§3). New agents are new adapters.
- **Source-agnostic.** A *source* is a `(location, agent)` pair. The primary source is **sandy sandboxes** (`$SANDY_HOME/sandboxes/*/`, enumerated via `sandy --print-state`); a later source is **host-native** installs (`~/.claude`, `~/.gemini`, …). lore does not require sandy — it requires *a* source.
- **v0 reads accumulated memory + context files**, not raw session transcripts (`*.jsonl` rollouts/history). Transcripts are deferred (§10).

---

## 2. Sources & enumeration

1. **sandy sandboxes (preferred).** Parse `sandy --print-state` JSON → for each sandbox: dir name, canonical `workspace`, `lock_holder_alive`. Within a sandbox, each agent's state lives in a known subdir (`claude/`, `gemini/`, `codex/`, `opencode/{config,share}`).
2. **Filesystem fallback.** Walk `$SANDY_HOME/sandboxes/*/` (default `~/.sandy`). Lock state then unknown (`null`); mutation fails closed (§7).
3. **`--source host`** (post-v0): read the agents' host-native dirs directly.
4. **`--sandboxes-root <dir>`** overrides discovery (tests against synthetic fixtures; non-default `SANDY_HOME`).

Project instruction files (`CLAUDE.md` / `GEMINI.md` / `AGENTS.md`) live in the **workspace** (the repo), while accumulated memory lives in the **agent state dir**. lore reads accumulated memory by default; instruction files are an opt-in second class (`--include-instructions`).

---

## 3. Agents & adapters

Each adapter maps an agent's on-disk memory/context to the normalized record (§4). Verified mid-2026; **all of these are version-dependent** — adapters must degrade gracefully and never hard-fail on an unexpected layout.

| Agent | Native auto-memory | Location (in a sandbox: under the agent subdir) | Instruction files | Format | Reliability | lore may mutate? |
|---|---|---|---|---|---|---|
| **claude** | Yes (on by default, CC ≥ 2.1.59) | `claude/projects/<repo>/memory/` — `MEMORY.md` index + topic `*.md`; frontmatter **optional** | `CLAUDE.md` (workspace + `~/.claude/CLAUDE.md`) | markdown | **high** (documented, stable path) | **yes**, under §7 |
| **gemini** | Yes (`/memory add`) | `gemini/GEMINI.md` (global); `/memory` appends here — *exact target version-dependent* | `GEMINI.md` (hierarchical, `@`-imports) | markdown | medium | cautious (append-style) |
| **codex** | Yes (opt-in: `[features] memories=true`; regionally gated) | `codex/memories/` | `AGENTS.md` + `config.toml` | "generated state" (markdown summaries over JSONL); **layout uncontracted** | **low** | **NO — read-only** |
| **opencode** | No (core) | — (3rd-party plugins only, e.g. `~/.config/opencode/memory/`) | `AGENTS.md` (+ `~/.claude/CLAUDE.md` fallback) | markdown | n/a (instructions only) | instructions only |

**Hard rules from the above:**
- **Codex `memories/` is read-only.** Official guidance is "treat as generated state, don't hand-edit; update `AGENTS.md` instead." lore reads it (cautiously, tolerating format drift) and **never** lists it as a mutation target.
- **Gemini** native memory is append-structured into a `GEMINI.md`; lore treats it as one document, not a directory of facts.
- **OpenCode** contributes only instruction files in core; lore does **not** assume any plugin memory path (a plugin adapter can be added later).
- Frontmatter (`name`/`description`/`type`/`originSessionId`) is **Claude-this-harness enrichment**, parsed when present, never required.

References: Claude `code.claude.com/docs/en/memory`; Gemini `github.com/google-gemini/gemini-cli` (`docs/cli/gemini-md.md`, commands); Codex `developers.openai.com/codex/memories`; OpenCode `opencode.ai/docs/rules`.

---

## 4. Normalized record

```
MemoryItem {
  agent: claude | gemini | codex | opencode
  source: str             # e.g. "sandbox:myproj-a1b2c3d4" or "host"
  source_kind: auto_memory | instructions
  project: str            # humanized label: workspace basename from the sandbox's
                          # WORKSPACE.json (NOT --print-state, which omits it),
                          # falling back to a humanized project_slug
  project_slug: str       # the agent's on-disk project dir name — uniqueness +
                          # link-resolution scope (a sandbox may hold several)
  path: str               # absolute file path
  title: str              # frontmatter name → first heading → filename stem
  body: str
  mtime: float
  # optional enrichment (Claude frontmatter; absent for plain-markdown agents):
  description: str?
  type: str?              # frontmatter `type` (captured top-level OR under
                          # metadata:); "unknown" if absent. Parsing is tolerant:
                          # known keys (name/title, description, type,
                          # originSessionId) are extracted, everything else is
                          # ignored, and only a broken (unterminated) fence warns.
  origin_session_id: str?
  links: [str]            # [[wikilinks]] — common in Claude, rare elsewhere
  in_index: bool?         # listed in MEMORY.md
  # adapter flags:
  readonly: bool          # true ⇒ never a mutation target (e.g. codex)
  parse_warning: str?
}
```

The link graph (edges = `[[name]]`) is built where links exist; resolved vs **dangling** edges are reported by `stats`. Per-project scope by default; `--cross-project` opt-in.

---

## 5. Command reference

Global flags: `--agent A[,B]`, `--source sandbox|host`, `--sandboxes-root <dir>`, `--sandy-home <dir>`, `--include-instructions`, `--json`, `-q/-v`. Output records always carry `agent`, so any command can be filtered/grouped by agent.

### 5.1 Read-only (offline, no LLM)
- **`ls` / `list`** `[--agent A] [--type T] [--project P] [--sort name|mtime]` — projects **A–Z**, then a **flat A–Z-by-title** list per project with the `type` shown inline (`name` is the default; `mtime` = newest first).
- **`search <query>`** `[--agent A] [--field title|description|body|all]` — ranked substring/token match.
- **`show <title>`** `[--project P] [--depth N]` — a memory + its link neighborhood.
- **`graph`** `[--project P] [--dot] [--cross-project]` — link graph (text tree / graphviz). Marks dangling edges. (Sparse for non-Claude agents.)
- **`stats`** — **coverage** (sandboxes *enumerated* vs. *with memory*, so a sparse result is legibly "no memory there", not a miss); counts by agent / type / project; index/file mismatches; dangling links; mtime growth. The coverage line is also emitted on stderr under `-v` for any command.
- **`export`** `[--md | --json] [--agent A] [--project P]` — consolidated digest. `--json` is the stable machine schema (§4).

### 5.2 LLM-powered (opt-in; require `claude` on `PATH`)
- **`summarize`** `[--agent A] [--project P] [--type T] [--model M]` — digest "what's been learned," grouped by theme, flagging contradictions; map-reduced when the selection exceeds a char budget.
- **`relevant <project>`** `[--model M] [--top N] [--explain]` — memories from *other* projects/agents that may apply here (§6.2); advisory only, never copies.

### 5.3 Mutating (require `--apply`; else dry-run; honor §3 + §7)
- **`dedup`** `[--llm] [--threshold X]` — candidate clusters (§6.1); `--llm` adjudicates. Read-only without `--merge --apply`.
- **`merge <title>... --into <title>`** `[--apply]` — union into a target, back up, rewrite `MEMORY.md`.
- **`prune <title>...`** `[--apply]` — remove + back up + de-index.
- **`copy <title> --to <project>`** `[--apply]` — the explicit "controlled bleed."

`copy`/`merge`/`prune`/`dedup --apply` **refuse any `readonly` item** (Codex) and any locked sandbox (§7).

### 5.4 Exit codes
`0` ok; `1` runtime/refusal; `2` usage. `--json` errors → `{"error": "..."}` on stderr.

---

## 5b. Sessions (transcripts)

A separate surface from memory — *deterministic* characterization of session transcripts (no LLM). Claude session transcripts live as `<sandbox>/claude/projects/<slug>/*.jsonl` (next to `memory/`). They are large (tens of MB) and the JSONL schema is **undocumented and version-stamped per event**, so the scanner **streams line-by-line** (never loads whole), tolerates unknown/garbled events, and never hard-fails.

- **`sessions`** `[--project P] [--sort title|started|duration|events]` — one profile per transcript, projects **A–Z**, then **A–Z by title** within each (`title` default): title, start date, duration, user/assistant message counts, top tools, branch.
- **`session <id|prefix|title>`** — full profile of one session (disambiguates a non-unique match → exit 1, list candidates).

**`SessionProfile`** (the `--json` schema), extracted in one streaming pass:

```
session_id, source, project, project_slug, path,
title (from `ai-title` events → first prompt → id),
started, ended, duration_s,
n_events, n_user, n_assistant,
tools{name->count}, files_touched[] (from Edit/Write tool inputs, deduped),
git_branch, model, version (Claude Code version),
pr_urls[] (from `pr-link` events), error_count, compact_count,
first_prompt, mtime, parse_warning
```

Transcripts are **Claude-only** in this increment (`--agent` excluding `claude` yields no sessions, not an error). Other agents' session logs and LLM "what happened" summaries are later increments (§10).

### Provenance (memory ↔ session)

A memory's frontmatter `originSessionId` and a transcript's `session_id` (its `<id>.jsonl` filename) match exactly, so lore bridges the two:

- **`show <memory>`** prints an `origin session:` line (title, date, duration) — or `(transcript not found)` if the id doesn't resolve. `--json` adds an `origin_session` object (or `null`).
- **`session <id>`** lists the **memories it produced** (those whose `originSessionId` == this session). `--json` adds `produced_memories[]`.
- **`sessions`** tags each session with `→ N mem`; `--json` adds `produced_memory_count`.
- **`stats`** reports a **provenance** block: sessions total / produced-memory / produced-none, and memories with/without a known origin session.

Provenance lookups are **cheap** — they list `*.jsonl` filenames (`session_id_paths`) to match ids and only scan the *one* origin transcript for `show`; `stats`/`sessions` never scan transcript bodies.

---

## 6. Algorithms

### 6.1 Duplicate / near-duplicate — two-stage
1. **Cheap clustering (always).** Token-shingle (2–3-gram, lowercased, destopworded) Jaccard over `title`+`description`+`body`; cluster above `--threshold` (default `0.5`). Identical `title` across projects is an automatic candidate. Deterministic, offline. Cross-agent clusters are surfaced but flagged (an agent's phrasing differs).
2. **Optional LLM adjudication (`--llm`).** Only candidate clusters go to `claude -p`, labeled `duplicate|overlapping|distinct|contradictory` with a proposed merge. Bounds LLM cost to clusters, not pairs.

### 6.2 Cross-source relevance
Shortlist by max token-overlap to the target project's corpus (top `N`, default 10) → opt-in LLM rerank with one-line rationales. Suggestion only; `copy` is the separate explicit step.

### 6.3 Stale flagging (advisory, never auto-acts)
Flag when: `origin_session_id`'s sandbox no longer exists; or a `project`/`feedback` item older than `--stale-days` (default 120) unreferenced by any newer item's links. A review hint, not a deletion trigger.

---

## 7. Mutation & safety

1. **Dry-run default.** Without `--apply`, print a unified diff of every change (incl. `MEMORY.md` lines) and exit `0`.
2. **Backup first.** Copy each to-be-changed file to `$SANDY_HOME/lore-backups/<UTC>/<source>/<project>/` (printed).
3. **Index consistency.** `merge`/`prune` rewrite the affected index line(s) atomically; lore never leaves a file/index mismatch it made.
4. **Lock gating.** Refuse to mutate a sandbox with `lock_holder_alive: true`. Refuse `null` (unknown) unless `--force` + warn.
5. **Read-only adapters.** Never mutate any item with `readonly: true` (Codex `memories/`) — refuse with a pointer to edit `AGENTS.md` instead.
6. **Atomic per file.** temp-file + `rename()`; partial-batch failure reports what remains.

---

## 8. LLM integration

Shell out to `claude -p "<prompt>"` (honoring `SANDY_MODEL`/`--model`); reuse the user's `claude` auth — no API key. Prompts use `title`+`description`+`body` text only. Output is advisory prose/suggestions, never written to a file without a subsequent explicit mutating command + `--apply`. Absent `claude` ⇒ LLM commands exit `1`; read-only commands unaffected.

---

## 9. Configuration

| Var / flag | Meaning | Default |
|---|---|---|
| `SANDY_HOME` | state root (sandboxes under `$SANDY_HOME/sandboxes`) | `~/.sandy` |
| `--source` | `sandbox` (default) or `host` (post-v0) | `sandbox` |
| `--agent` | restrict to agent(s) | all |
| `--sandboxes-root` / `--sandy-home` | discovery overrides | from `SANDY_HOME` |
| `SANDY_MODEL` / `--model` | LLM model | claude default |
| `--threshold` / `--stale-days` | dedup/relevance cutoff / stale age | `0.5` / `120` |

---

## 10. Non-goals (v0)

- **Deterministic session profiles are now IN** (§5b). Still out: **memory↔session provenance** (`originSessionId` ↔ `session_id`), **LLM "what happened" summaries** (needs aggressive transcript reduction first), **full-text transcript search**, and **`history.jsonl`**.
- **Embeddings** — v0 uses token-overlap + opt-in LLM; revisit only if heuristics prove weak (accepts a dependency/provider cost).
- **OpenCode plugin memory & writing Codex memory** — out by rule (no core feature / generated-state).
- **Authoring new memories** except via explicit `copy`/`merge`.
- **A daemon / TUI** — v0 is a stateless per-command CLI.
