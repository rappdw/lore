"""Shared test helpers: load the extensionless `lore` as a module, run it, build fixtures."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import types


def load_lore():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, os.pardir, "lore")
    # The executable has no .py suffix, so name the loader explicitly. Register
    # in sys.modules before exec so dataclasses can resolve its own annotations
    # (with `from __future__ import annotations`, type lookup needs the module).
    loader = importlib.machinery.SourceFileLoader("lore", path)
    spec = importlib.util.spec_from_loader("lore", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lore"] = mod
    loader.exec_module(mod)
    return mod


def run(mod, argv):
    """Invoke main(argv); return (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mod.main(argv)
    return code, out.getvalue(), err.getvalue()


def args_ns(**kw):
    """A minimal args namespace for calling collect_items/discover_sources directly."""
    ns = types.SimpleNamespace(
        sandboxes_root=None, sandy_home=None, agent=None,
        type=None, project=None, verbosity=0, json=False, source="sandbox",
    )
    ns.__dict__.update(kw)
    return ns


def _w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build_fixture(root):
    """Synthetic multi-sandbox/multi-project tree (driven via --sandboxes-root).

    Covers: 2 populated sandboxes + 1 empty; 2 project slugs in one sandbox;
    Claude memory WITH and WITHOUT frontmatter; an unterminated-frontmatter file;
    a bad `type`; a duplicate title across projects; a MEMORY.md that indexes a
    missing file (ghost) and omits a present file (orphan); dangling + cross-project links.
    """
    sb = os.path.join(root, "sandboxes")

    # ── sandbox 1: zork (two project slugs) ──
    z = os.path.join(sb, "zork-aaaa1111")
    _w(os.path.join(z, "WORKSPACE.json"), '{"workspace_path": "/Users/x/dev/zork"}\n')
    zmem = os.path.join(z, "claude", "projects", "-Users-x-dev-zork", "memory")
    _w(os.path.join(zmem, "MEMORY.md"),
       "# Index\n\n"
       "- [Alpha](alpha.md) — the alpha\n"
       "- [Beta](beta.md) — the beta\n"
       "- [broken](broken.md) — malformed fm\n"
       "- [Common](common.md) — shared title\n"
       "- [Ghost](ghost.md) — index entry with no file\n")
    _w(os.path.join(zmem, "alpha.md"),
       "---\nname: alpha\ndescription: first thing\nmetadata:\n"
       "  type: project\n  originSessionId: sess-aaaa1111\n---\n\n"  # matches a fixture session
       "Alpha body links [[beta]] and [[nowhere]].\n")
    _w(os.path.join(zmem, "beta.md"), "# Beta\n\nBeta has no frontmatter. See [[alpha]].\n")
    _w(os.path.join(zmem, "common.md"), "---\nname: common\nmetadata:\n  type: project\n---\n\nShared name (zork).\n")
    _w(os.path.join(zmem, "orphan.md"), "---\nname: orphan\nmetadata:\n  type: reference\n---\n\nPresent but not indexed.\n")
    _w(os.path.join(zmem, "broken.md"), "---\nname: broken\ndescription: oops\n\nbody, but the fence never closed\n")
    znotes = os.path.join(z, "claude", "projects", "-Users-x-dev-zork-notes", "memory")
    _w(os.path.join(znotes, "MEMORY.md"), "- [Gamma](gamma.md) — notes\n")
    _w(os.path.join(znotes, "gamma.md"), "---\nname: gamma\nmetadata:\n  type: user\n---\n\nGamma links [[delta]] (cross-project).\n")

    # ── sandbox 2: mylib ──
    m = os.path.join(sb, "mylib-bbbb2222")
    _w(os.path.join(m, "WORKSPACE.json"), '{"workspace_path": "/Users/x/dev/mylib"}\n')
    mmem = os.path.join(m, "claude", "projects", "-Users-x-dev-mylib", "memory")
    _w(os.path.join(mmem, "MEMORY.md"),
       "- [Delta](delta.md) — ref\n- [Epsilon](epsilon.md) — stem title\n"
       "- [Common](common.md) — shared title\n- [Zeta](zeta.md) — bad type\n")
    _w(os.path.join(mmem, "delta.md"),
       "---\nname: delta\ndescription: a reference\nmetadata:\n  type: reference\n  originSessionId: sess-9\n---\n\nDelta body.\n")
    _w(os.path.join(mmem, "epsilon.md"), "epsilon has no frontmatter and no heading line\n")
    _w(os.path.join(mmem, "common.md"), "---\nname: common\nmetadata:\n  type: reference\n---\n\nShared name (mylib).\n")
    _w(os.path.join(mmem, "zeta.md"), "---\nname: zeta\nmetadata:\n  type: bogus\n---\n\nZeta has a bad type.\n")

    # two session transcripts next to zork's memory dir (project-dir level).
    # sess-bbbb is started EARLIER but titled "zzz-later" — so default title-sort
    # (A–Z) must put "build-the-thing" first, distinguishing it from started-sort.
    _w(os.path.join(os.path.dirname(zmem), "sess-aaaa1111.jsonl"), _session_jsonl())
    _w(os.path.join(os.path.dirname(zmem), "sess-bbbb2222.jsonl"), _session_jsonl2())

    # ── sandbox 3: empty (no memory) ──
    e = os.path.join(sb, "empty-cccc3333")
    os.makedirs(os.path.join(e, "claude", "projects", "-void", "memory"), exist_ok=True)
    return root


def _session_jsonl():
    """A small but representative transcript: timestamps, tool_use, ai-title,
    pr-link, a compaction, an api error, a dedup'd file, plus a malformed line."""
    ev = [
        {"type": "user", "timestamp": "2026-06-01T10:00:00.000Z", "gitBranch": "main",
         "version": "2.1.0", "message": {"role": "user", "content": "build the thing"}},
        {"type": "assistant", "timestamp": "2026-06-01T10:00:05.000Z",
         "message": {"role": "assistant", "model": "claude-opus-4-8", "content": [
             {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
             {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x/a.py"}}]}},
        {"type": "ai-title", "aiTitle": "build-the-thing"},
        {"type": "pr-link", "timestamp": "2026-06-01T10:30:00.000Z",
         "prUrl": "https://github.com/x/y/pull/1", "prNumber": 1},
        {"type": "assistant", "timestamp": "2026-06-01T11:00:00.000Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x/a.py"}}]}},  # dup file
        {"type": "system", "timestamp": "2026-06-01T11:00:01.000Z", "compactMetadata": {"trigger": "auto"}},
        {"type": "user", "timestamp": "2026-06-01T11:05:00.000Z", "apiErrorStatus": 500,
         "message": {"role": "user", "content": [{"type": "tool_result"}]}},
    ]
    lines = [json.dumps(e) for e in ev]
    lines.append("this is not json")  # must be tolerated, not counted
    lines.append("")                  # blank line
    return "\n".join(lines) + "\n"


def _session_jsonl2():
    """A second, earlier session titled 'zzz-later' (sorts last alphabetically)."""
    ev = [
        {"type": "user", "timestamp": "2026-05-01T09:00:00.000Z", "gitBranch": "dev",
         "message": {"role": "user", "content": "earlier session"}},
        {"type": "ai-title", "aiTitle": "zzz-later"},
        {"type": "assistant", "timestamp": "2026-05-01T09:01:00.000Z",
         "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Read", "input": {}}]}},
    ]
    return "\n".join(json.dumps(e) for e in ev) + "\n"
