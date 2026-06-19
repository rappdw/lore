import json
import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, args_ns, run

lore = load_lore()


class TestSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-sess-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")
        cls.sessions = lore.discover_sessions(args_ns(sandboxes_root=cls.root))
        cls.s = next(s for s in cls.sessions if s.session_id == "sess-aaaa1111")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sessions_discovered(self):
        self.assertEqual(len(self.sessions), 2)
        self.assertEqual(self.s.project, "zork")

    def test_default_order_alphabetical(self):
        # default --sort title: "build-the-thing" must precede "zzz-later",
        # even though zzz-later started earlier (proves title-sort, not date).
        code, out, _ = self._lore("sessions")
        self.assertEqual(code, 0)
        self.assertLess(out.index("build-the-thing"), out.index("zzz-later"))

    def test_counts_and_tolerance(self):
        # 7 well-formed events; the "not json" + blank lines are skipped, not counted.
        self.assertEqual(self.s.n_events, 7)
        self.assertEqual(self.s.n_user, 2)
        self.assertEqual(self.s.n_assistant, 2)

    def test_title_timing_context(self):
        self.assertEqual(self.s.title, "build-the-thing")
        self.assertEqual(self.s.git_branch, "main")
        self.assertEqual(self.s.model, "claude-opus-4-8")
        self.assertEqual(self.s.version, "2.1.0")
        self.assertEqual(self.s.duration_s, 65 * 60)  # 10:00 -> 11:05

    def test_tools_and_files_dedup(self):
        self.assertEqual(self.s.tools, {"Bash": 1, "Edit": 2})
        self.assertEqual(self.s.files_touched, ["/x/a.py"])  # deduped

    def test_prs_errors_compactions_prompt(self):
        self.assertEqual(self.s.pr_urls, ["https://github.com/x/y/pull/1"])
        self.assertEqual(self.s.error_count, 1)
        self.assertEqual(self.s.compact_count, 1)
        self.assertEqual(self.s.first_prompt, "build the thing")

    def _lore(self, *argv):
        return run(lore, list(argv) + ["--sandboxes-root", self.root])

    def test_sessions_command(self):
        code, out, _ = self._lore("sessions")
        self.assertEqual(code, 0)
        self.assertIn("build-the-thing", out)
        self.assertIn("Bash×1", out)

    def test_sessions_json(self):
        code, out, _ = self._lore("sessions", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["count"], 2)
        s = [x for x in d["sessions"] if x["session_id"] == "sess-aaaa1111"][0]
        self.assertEqual(s["files_touched"], ["/x/a.py"])

    def test_session_detail_by_prefix(self):
        code, out, _ = self._lore("session", "sess-aaaa")
        self.assertEqual(code, 0)
        self.assertIn("pull/1", out)
        self.assertIn("files touched (1)", out)
        self.assertIn("opening prompt: build the thing", out)

    def test_session_by_title(self):
        code, out, _ = self._lore("session", "build-the")
        self.assertEqual(code, 0)
        self.assertIn("build-the-thing", out)

    def test_session_missing_exits_1(self):
        code, _, _ = self._lore("session", "nope-nope")
        self.assertEqual(code, 1)

    def test_agent_filter_excludes_claude(self):
        # transcripts are claude-only; --agent gemini yields no sessions, not an error.
        code, out, _ = self._lore("sessions", "--agent", "gemini", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["count"], 0)


if __name__ == "__main__":
    unittest.main()
