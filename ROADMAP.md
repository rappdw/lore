# lore — Roadmap

Direction and milestones. The near-term build sequence lives in [PLAN.md](PLAN.md); this is the longer view — what ships when, and what is deliberately deferred.

## Guiding principles

- **Isolation by default, introspection on demand.** lore must never become a back door that silently re-merges what sandy deliberately isolates. Cross-context actions are always explicit.
- **Agent-agnostic, not Claude-shaped.** The core is a normalized record + per-agent adapters. New agents are new adapters; the core assumes only "markdown."
- **Read-only is the safe default; mutation is gated.** The everyday surface (explore, search, summarize) never writes. Curation is opt-in, dry-run-first, reversible — and never touches generated state (Codex) or a locked session.
- **Single file, zero dependencies.** Like sandy. The moment we "need" a library is the moment to reconsider the feature.

## Milestones

### `0.1.0` — Core + Claude, read-only (M-a)
The adapter framework, the Claude adapter, the read-only memory commands (`ls`/`search`/`show`/`graph`/`stats`/`export`), **deterministic session profiles** (`sessions`/`session`), and the **memory↔session provenance bridge**: `show` reveals the session a memory came from, `session` lists the memories it produced, and `stats`/`sessions` flag sessions that produced none. Offline, no LLM, no mutation. **Proves the data model and that a cross-project lens is useful** — against the richest, most reliable source first.

### `0.2.0` — Summarize & relate (M-b)
`summarize` (digest of what the agents have learned) and `relevant <project>` (controlled, advisory cross-pollination) via the `claude` CLI. The insight layer — and it pays off immediately against the rich Claude memory that already exists.

### `0.3.0` — Curation (M-c)
`dedup` / `merge` / `prune` / `copy` behind the full safety model. The "tend the garden" layer.

### `0.4.0` — All agents, read-only (M-d)
Gemini, Codex (read-only), and OpenCode adapters. **"Regardless of harness" becomes real**: one lens over every agent's memory, normalized and grouped by agent. (Moved after the insight/curation layers — those deliver value on the Claude corpus you have today, whereas other-agent memory is still sparse.)

### `0.5.0` — Soak & polish
Daily-drive across a real multi-project, multi-agent sandbox collection. Verify the per-agent real-install layouts (Gemini/Codex paths are version-dependent). Tune dedup/relevance thresholds against real memory. Stabilize output formats.

### `1.0.0` — Stable
Command surface and `export --json` schema frozen under a stability promise (mirroring sandy's introspection posture). Published install path (after the `lore` binary-name collision check).

## Deferred — candidates beyond 1.0 (not commitments)

- **Host-native source (`--source host`).** Read agents' real install dirs (`~/.claude`, `~/.gemini`, `~/.codex`) directly, not only sandy sandboxes — making lore useful even without sandy.
- **Transcripts / sessions.** ✅ **Deterministic session profiles** (`sessions`/`session`) and ✅ **memory↔session provenance** (`originSessionId` ↔ `session_id`) both shipped in `0.1.0`. Still ahead, in order of value: **LLM "what happened" summaries** (needs aggressive transcript reduction — ~98% of the bytes are tool results), **full-text transcript search**, and `history.jsonl`. Kept a separate surface from memory by design.
- **Embeddings.** Swap token-overlap for a local/hosted embedding model behind the same dedup/relevance interfaces, *if* heuristics prove insufficient — accepting the dependency/provider cost.
- **OpenCode plugin memory.** A pluggable sub-adapter for the third-party memory plugins (`opencode-agent-memory`, etc.), once one is common enough to be worth it.
- **TUI / watch mode.** An interactive browser over the graph, or a `watch` that surfaces relevant prior memories as you start work in a project.
- **Its own repository.** ✅ Done — graduated out of `sandy/` into a standalone repo, versioned independently (sandy is a documented dependency via `--print-state`, not a parent).
- **Promote-to-shared.** A reviewed path for elevating a broadly-true `user`/`feedback` memory into something seeded across new sandboxes — the careful, opt-in inverse of isolation.

## Open questions

- Per-project the right default graph scope, or should cross-project links resolve by default once slug-collision risk is measured on real data?
- Should `relevant` run automatically (advisory) at the start of a sandy session via a hook, or stay a manual pull? (Leaning manual until trust is established.)
- Codex `memories/` is "generated state" with an uncontracted, drifting layout — is read-cautiously enough, or should it be opt-in (`--agent codex` required) so a format change never noisily breaks the default view?
- Backup retention / GC policy for `lore-backups/`.
- `lore` binary-name collision (kernel `lore`, others) — resolve before publishing an install path.
