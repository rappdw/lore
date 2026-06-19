import json
import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, run

lore = load_lore()


class TestProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-prov-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")
        # fixture wiring: alpha.md -> originSessionId sess-aaaa1111 (titled "build-the-thing");
        # delta.md -> sess-9 (no matching transcript); session sess-bbbb2222 produces nothing.

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lore(self, *argv):
        return run(lore, list(argv) + ["--sandboxes-root", self.root])

    def test_show_bridges_to_origin_session(self):
        code, out, _ = self.lore("show", "alpha")
        self.assertEqual(code, 0)
        self.assertIn("origin session:", out)
        self.assertIn("build-the-thing", out)

    def test_show_json_origin_session(self):
        code, out, _ = self.lore("show", "alpha", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertIsNotNone(d["origin_session"])
        self.assertEqual(d["origin_session"]["title"], "build-the-thing")

    def test_show_unresolvable_origin(self):
        # delta's originSessionId (sess-9) has no transcript -> "transcript not found".
        code, out, _ = self.lore("show", "delta")
        self.assertEqual(code, 0)
        self.assertIn("transcript not found", out)

    def test_session_lists_produced_memories(self):
        code, out, _ = self.lore("session", "sess-aaaa1111", "--json")
        self.assertEqual(code, 0)
        titles = [m["title"] for m in json.loads(out)["produced_memories"]]
        self.assertIn("alpha", titles)

    def test_sessions_produced_count_tag(self):
        code, out, _ = self.lore("sessions", "--json")
        self.assertEqual(code, 0)
        by_id = {s["session_id"]: s for s in json.loads(out)["sessions"]}
        self.assertEqual(by_id["sess-aaaa1111"]["produced_memory_count"], 1)
        self.assertEqual(by_id["sess-bbbb2222"]["produced_memory_count"], 0)

    def test_stats_provenance(self):
        code, out, _ = self.lore("stats", "--json")
        self.assertEqual(code, 0)
        p = json.loads(out)["provenance"]
        self.assertEqual(p["sessions_total"], 2)
        self.assertEqual(p["sessions_with_memory"], 1)     # sess-aaaa
        self.assertEqual(p["sessions_without_memory"], 1)  # sess-bbbb
        self.assertEqual(p["memories_with_origin"], 1)     # alpha (delta's sess-9 unresolvable)


if __name__ == "__main__":
    unittest.main()
