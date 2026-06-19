import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, args_ns

lore = load_lore()


class TestGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-graph-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")
        cls.items = lore.collect_items(args_ns(sandboxes_root=cls.root))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _dangling_targets(self, cross):
        g = lore.build_graph(self.items, cross)
        return sorted(ln for _, ln in g.dangling)

    def test_per_project_resolution_and_dangling(self):
        # alpha->beta resolves (same project); alpha->nowhere dangles;
        # gamma->delta dangles per-project (delta is in a different project).
        targets = self._dangling_targets(cross=False)
        self.assertIn("nowhere", targets)
        self.assertIn("delta", targets)

    def test_cross_project_resolves_delta(self):
        targets = self._dangling_targets(cross=True)
        self.assertIn("nowhere", targets)        # still unknown
        self.assertNotIn("delta", targets)       # now resolves across projects

    def test_resolved_edge_points_to_item(self):
        g = lore.build_graph(self.items, False)
        resolved = [(s.title, t.title) for s, ln, t, r in g.edges if r]
        self.assertIn(("alpha", "Beta"), resolved)

    def test_neighbors_depth_cycle_guarded(self):
        # alpha <-> beta is a cycle; depth=3 must terminate, not loop.
        g = lore.build_graph(self.items, False)
        alpha = next(it for it in self.items if it.title == "alpha")
        neighbors = lore._neighbors(alpha, g, 3)
        titles = [n.title for n in neighbors]
        self.assertIn("Beta", titles)
        self.assertEqual(len(titles), len(set(titles)))  # no repeats


if __name__ == "__main__":
    unittest.main()
