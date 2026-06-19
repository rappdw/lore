import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, args_ns

lore = load_lore()


class TestClaudeAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-adapter-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")
        cls.items = lore.collect_items(args_ns(sandboxes_root=cls.root))
        cls.by_title = {it.title: it for it in cls.items}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_total_count(self):
        # zork: alpha,beta,common,orphan,broken (5) + notes: gamma (1) + mylib: delta,epsilon,common,zeta (4)
        self.assertEqual(len(self.items), 10)

    def test_title_precedence(self):
        self.assertIn("alpha", self.by_title)        # frontmatter name
        self.assertIn("Beta", self.by_title)         # first heading
        self.assertIn("epsilon", self.by_title)      # filename stem

    def test_type_unknown_when_absent(self):
        self.assertEqual(self.by_title["Beta"].type, "unknown")
        self.assertEqual(self.by_title["epsilon"].type, "unknown")

    def test_bad_type_warns_but_loads(self):
        zeta = self.by_title["zeta"]
        self.assertEqual(zeta.type, "bogus")
        self.assertIn("unknown type: bogus", zeta.parse_warning)

    def test_in_index_flag(self):
        self.assertIs(self.by_title["orphan"].in_index, False)
        self.assertIs(self.by_title["alpha"].in_index, True)

    def test_malformed_does_not_raise_and_warns(self):
        broken = self.by_title["broken"]
        self.assertEqual(broken.parse_warning, "unterminated frontmatter")

    def test_multiple_project_slugs(self):
        slugs = set(it.project_slug for it in self.items)
        self.assertIn("-Users-x-dev-zork", slugs)
        self.assertIn("-Users-x-dev-zork-notes", slugs)

    def test_empty_sandbox_yields_nothing(self):
        self.assertEqual([it for it in self.items if it.source == "sandbox:empty-cccc3333"], [])

    def test_metadata_enrichment(self):
        alpha = self.by_title["alpha"]
        self.assertEqual(alpha.description, "first thing")
        self.assertEqual(alpha.origin_session_id, "sess-aaaa1111")
        self.assertEqual(alpha.project, "zork")
        self.assertFalse(alpha.readonly)
        self.assertEqual(alpha.source_kind, "auto_memory")


if __name__ == "__main__":
    unittest.main()
