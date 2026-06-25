"""`search` spanning memories + session transcripts (conversation by default,
`--all` for tool I/O), with `--memories-only`/`--sessions-only` scoping."""
import json
import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, run

lore = load_lore()


class TestSearchSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-ssearch-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lore(self, *argv):
        return run(lore, list(argv) + ["--sandboxes-root", self.root])

    def test_default_spans_both_surfaces(self):
        # "build" is in a session user prompt, not in any memory.
        code, out, _ = self.lore("search", "build", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["count"], 0)                       # no memory hits
        self.assertEqual(d["session_count"], 1)
        s = d["sessions"][0]
        self.assertEqual(s["session_id"], "sess-aaaa1111")
        self.assertEqual(s["hits"][0]["role"], "user")
        self.assertEqual(s["hits"][0]["source"], "prompt")

    def test_memories_only_skips_sessions(self):
        code, out, _ = self.lore("search", "build", "--memories-only")
        self.assertEqual(code, 0)
        self.assertIn("No matches", out)                      # session prompt not scanned

    def test_sessions_only_skips_memories(self):
        code, out, _ = self.lore("search", "build", "--sessions-only", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["count"], 0)
        self.assertEqual(d["session_count"], 1)

    def test_tool_io_excluded_by_default(self):
        # "ls" is only in a Bash tool_use input — not conversation text.
        code, out, _ = self.lore("search", "ls", "--sessions-only")
        self.assertEqual(code, 0)
        self.assertIn("No matches", out)

    def test_all_flag_searches_tool_input(self):
        code, out, _ = self.lore("search", "ls", "--all", "--sessions-only", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["session_count"], 1)
        self.assertEqual(d["sessions"][0]["hits"][0]["source"], "tool_input")

    def test_matches_second_session(self):
        code, out, _ = self.lore("search", "earlier", "--sessions-only", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual([s["session_id"] for s in d["sessions"]], ["sess-bbbb2222"])

    def test_project_filter(self):
        code, out, _ = self.lore("search", "build", "--sessions-only",
                                 "--project", "mylib", "--json")
        self.assertEqual(json.loads(out)["session_count"], 0)  # sessions are under zork

    def test_claude_only(self):
        code, out, _ = self.lore("search", "build", "--agent", "claude,gemini", "--json")
        self.assertEqual(code, 0)
        # gemini contributes no transcripts; the claude session still matches.
        self.assertEqual(json.loads(out)["session_count"], 1)

    def test_conflicting_scope_flags_usage_error(self):
        code, _, err = self.lore("search", "x", "--memories-only", "--sessions-only")
        self.assertEqual(code, 2)
        self.assertIn("mutually exclusive", err)

    def test_memory_search_unchanged(self):
        # Back-compat: `items` still carries memory hits, ranked title-first.
        code, out, _ = self.lore("search", "alpha", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["items"][0]["title"], "alpha")


if __name__ == "__main__":
    unittest.main()
