import json
import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, run

lore = load_lore()


class TestCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-cmd-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lore(self, *argv):
        return run(lore, list(argv) + ["--sandboxes-root", self.root])

    def test_ls_ok(self):
        code, out, _ = self.lore("ls")
        self.assertEqual(code, 0)
        self.assertIn("zork", out)
        self.assertIn("mylib", out)

    def test_ls_json_count(self):
        code, out, _ = self.lore("ls", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["count"], 10)

    def test_ls_flat_alphabetical_layout(self):
        # Flat A–Z per project: type shown inline as [type], no type sub-headers.
        code, out, _ = self.lore("ls")
        self.assertEqual(code, 0)
        self.assertIn("[project]", out)        # type inline tag
        self.assertNotIn("    project:", out)  # old type sub-header gone

    def test_search_ranks_title_over_body(self):
        # "alpha": title hit (alpha.md) must outrank body hit (beta mentions [[alpha]]).
        code, out, _ = self.lore("search", "alpha", "--json")
        self.assertEqual(code, 0)
        items = json.loads(out)["items"]
        self.assertEqual(items[0]["title"], "alpha")

    def test_show_neighborhood_and_dangling(self):
        code, out, _ = self.lore("show", "alpha")
        self.assertEqual(code, 0)
        self.assertIn("Alpha body links", out)
        self.assertIn("Beta", out)               # resolved link
        self.assertIn("nowhere (dangling)", out)  # dangling link

    def test_show_ambiguous_exits_1(self):
        code, _, err = self.lore("show", "common")
        self.assertEqual(code, 1)
        self.assertIn("ambiguous", err)

    def test_show_missing_exits_1(self):
        code, _, _ = self.lore("show", "does-not-exist")
        self.assertEqual(code, 1)

    def test_stats_reports_mismatches_and_dangling(self):
        code, out, _ = self.lore("stats", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertTrue(any("orphan.md" in p for p in d["mismatches"]["file_without_index"]))
        self.assertTrue(any(e["slug"] == "ghost.md" for e in d["mismatches"]["index_without_file"]))
        self.assertTrue(any(e["to"] == "nowhere" for e in d["dangling"]))

    def test_export_json_schema_keys(self):
        code, out, _ = self.lore("export", "--json")
        self.assertEqual(code, 0)
        item = json.loads(out)["items"][0]
        expected = ["agent", "source", "source_kind", "project", "project_slug", "path",
                    "title", "type", "description", "origin_session_id", "links", "in_index",
                    "readonly", "mtime", "mtime_iso", "parse_warning", "body"]
        self.assertEqual(list(item.keys()), expected)

    def test_graph_dot(self):
        code, out, _ = self.lore("graph", "--dot")
        self.assertEqual(code, 0)
        self.assertIn("digraph lore {", out)

    def test_filter_by_type(self):
        code, out, _ = self.lore("ls", "--type", "reference", "--json")
        self.assertEqual(code, 0)
        for it in json.loads(out)["items"]:
            self.assertEqual(it["type"], "reference")

    def test_bad_agent_is_usage_error(self):
        code, _, err = self.lore("ls", "--agent", "bogus")
        self.assertEqual(code, 2)
        self.assertIn("unknown agent", err)

    def test_known_unregistered_agent_yields_empty(self):
        # gemini is a known name but has no adapter in v0a -> empty, not an error.
        code, out, _ = self.lore("ls", "--agent", "gemini", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["count"], 0)

    def test_source_host_not_implemented(self):
        code, _, err = self.lore("ls", "--source", "host")
        self.assertEqual(code, 1)
        self.assertIn("not implemented", err)

    def test_stats_coverage(self):
        # fixture: zork + mylib + empty -> 3 enumerated, 2 with memory.
        code, out, _ = self.lore("stats", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["sandboxes_enumerated"], 3)
        self.assertEqual(d["sandboxes_with_memory"], 2)

    def test_verbose_emits_coverage(self):
        code, _, err = self.lore("ls", "-v")
        self.assertEqual(code, 0)
        self.assertIn("enumerated 3 sandbox", err)
        self.assertIn("2 with memory", err)

    def test_no_subcommand_usage(self):
        code, _, _ = run(lore, [])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
