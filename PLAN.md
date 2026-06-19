# lore — Implementation Plan

How we build what [SPECIFICATION.md](SPECIFICATION.md) describes, in testable increments. Each ships independently and is validated before the next begins.

Layout target:

```
lore/
  lore                      # the single-file executable (Python 3, no extension)
  README.md  CLAUDE.md  SPECIFICATION.md  PLAN.md  ROADMAP.md
  install.sh                # ~/.local/bin install (added in v0a)
  tests/
    fixtures/               # synthetic per-agent sandbox trees
    test_*.py               # stdlib unittest
    run.sh                  # runs the suite + `python3 -m py_compile lore`
```

---

## v0a — core + Claude adapter, read-only (target `0.1.0`)

The foundation: the adapter framework, the Claude adapter, and the read-only commands. **Fully testable inside a sandy container** via synthetic fixtures.

1. **CLI skeleton.** Argparse subcommands; global flags (`--agent`, `--source`, `--sandboxes-root`, `--sandy-home`, `--include-instructions`, `--json`, `-q/-v`); exit-code discipline (SPEC §5.4).
2. **Source enumeration.** `sandy --print-state` parse → `(name, workspace, lock_holder_alive)`; filesystem fallback over `$SANDY_HOME/sandboxes`; `--sandboxes-root` override.
3. **Adapter framework.** An `Adapter` interface (`discover(source) -> [MemoryItem]`) + a registry keyed by agent; the graceful-degradation contract (never hard-fail on layout).
4. **Claude adapter.** Walk `claude/projects/*/memory/`; parse `MEMORY.md` index + topic files; **optional** frontmatter enrichment; `[[links]]`; `readonly=false`.
5. **Link graph** (resolved vs dangling; per-project default, `--cross-project` opt-in).
6. **Commands.** `ls/list`, `search`, `show`, `graph` (text + `--dot`), `stats`, `export` (`--md`/`--json`).
7. **`install.sh`** + `--version`/`--help`.

**Tests** — fixture: ≥2 sandboxes, ≥2 projects, Claude memory both *with* and *without* frontmatter, a dangling link, an index/file mismatch, a malformed file. Assert enumeration, per-type/project counts, search ranking, `show` neighborhood, `stats` mismatches, `export --json` schema, graceful malformed handling.

**Exit criteria**: read-only commands work against the fixture and this container's own sandbox; `export --json` schema documented in SPEC §4; suite green.

---

## v0b — LLM: summarize & relate (target `0.2.0`)

`summarize` + `relevant`, via the Anthropic Messages API over stdlib HTTP (no SDK). The v0a core stays fully functional with no credential and no network. Sequenced first after the core because it pays off immediately on the rich Claude memory that already exists.

1. **LLM shim.** `urllib` POST to `/v1/messages`; `ANTHROPIC_API_KEY` from env or `$SANDY_HOME/.secrets` (a Claude Code OAuth token is *not* accepted — ToS); `--model`/`SANDY_MODEL`; timeout; clean "no key" exit.
2. **Token-overlap scorer (SPEC §6.1/§6.2 stage 1).** The shingle/Jaccard scorer — **built here, reused by curation (v0c)**. Deterministic, unit-tested offline (no LLM in CI).
3. **`summarize`.** Selection → bounded prompt → digest; map-reduce over the char budget.
4. **`relevant`.** Shortlist (via the scorer) → `--explain` LLM rerank with rationales; advisory only.

**Tests** — scorer is deterministic & unit-tested with no LLM; the LLM runner is injectable so `summarize`/`relevant` are testable stubbed.

**Exit criteria**: scorer correctness offline; LLM path verified on the host; documented that CI stubs the model.

---

## v0c — curation (target `0.3.0`)

The mutating commands behind SPEC §7. Highest-risk of the Claude-only increments — guarded throughout.

1. **Candidate clustering (SPEC §6.1).** Reuse the v0b shingle/Jaccard scorer; `--threshold`.
2. **Safety harness** (SPEC §7): dry-run diff; backup-before-write; atomic temp+rename; `MEMORY.md` index rewrite; **lock gating** (`lock_holder_alive`); **readonly refusal** (general rule — Claude items are mutable, so this is unit-tested against a *synthetic* `readonly=true` item; real Codex items arrive in v0d).
3. **`dedup`** (cluster report; `--llm` adjudication), **`merge`**, **`prune`**, **`copy`**.
4. **Stale flagging** (SPEC §6.3) — advisory, surfaced in `dedup`/`prune --dry-run`.

**Tests** — mutate a *copy* of a fixture; assert backups exist, index stays consistent, dry-run writes nothing, `--apply` writes exactly the diff, a locked sandbox is refused, a synthetic `readonly` item is refused, atomic-write leaves no partials.

**Exit criteria**: every mutating path has a dry-run test and an `--apply`-on-fixture test; no command writes to a locked sandbox or a `readonly` item; backups verified.

---

## v0d — the other agents' adapters, read-only (target `0.4.0`)

Where "regardless of harness" becomes real. **Moved last:** the insight (v0b) and curation (v0c) layers deliver value on the Claude corpus that exists today, whereas other-agent memory is still sparse.

1. **Gemini adapter.** `gemini/GEMINI.md` as a single `auto_memory` document; tolerate an absent/renamed target (version-dependent).
2. **Codex adapter.** `codex/memories/` → `readonly=true` items; tolerate the uncontracted/drifting layout — parse what's markdown, skip/flag the rest, **never crash on JSONL or an unexpected tree**.
3. **OpenCode adapter.** `AGENTS.md` instructions only (`source_kind=instructions`); assume no native memory store.
4. **`--include-instructions`** across agents (`CLAUDE.md`/`GEMINI.md`/`AGENTS.md` from the workspace).
5. **Cross-agent grouping/filtering** in `ls`/`search`/`stats`; the curation **readonly refusal** (v0c) now has real Codex items to act on.

**Tests** — per-agent fixtures including a deliberately malformed Codex `memories/` (assert no crash, `readonly` set, `parse_warning` recorded).

**Exit criteria**: all four adapters load their fixtures; Codex items are `readonly`; nothing hard-fails on layout drift. (Real-install verification of Gemini/Codex paths happens on the host.)

---

## Cross-cutting

- **No dependencies.** `python3 -m py_compile lore` + `tests/run.sh` are the gate; stdlib `unittest` only.
- **Host vs container.** All increments are unit-testable in-container via `--sandboxes-root` fixtures. The real multi-sandbox path, the per-agent real-install layouts, and the LLM path are validated **on the host** — same constraint as sandy's own suites.
- **Docs in lockstep.** Each increment updates SPECIFICATION.md + the README command table in the same change.
