import os
import shutil
import tempfile
import unittest
from _loader import load_lore, build_fixture, args_ns

lore = load_lore()


class TestEnumeration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-enum-")
        cls.root = build_fixture(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sandboxes_root_discovers_all(self):
        srcs = lore.discover_sources(args_ns(sandboxes_root=os.path.join(self.root, "sandboxes")))
        names = sorted(s.name for s in srcs)
        self.assertEqual(names, ["empty-cccc3333", "mylib-bbbb2222", "zork-aaaa1111"])

    def test_walk_fallback_lock_state_unknown(self):
        srcs = lore.discover_sources(args_ns(sandboxes_root=os.path.join(self.root, "sandboxes")))
        for s in srcs:
            self.assertIsNone(s.lock_holder_alive)

    def test_workspace_label_from_workspace_json(self):
        srcs = {s.name: s for s in
                lore.discover_sources(args_ns(sandboxes_root=os.path.join(self.root, "sandboxes")))}
        self.assertEqual(srcs["zork-aaaa1111"].label, "zork")
        self.assertEqual(srcs["mylib-bbbb2222"].label, "mylib")

    def test_missing_root_returns_empty(self):
        self.assertEqual(lore.discover_sources(args_ns(sandboxes_root="/no/such/dir")), [])


if __name__ == "__main__":
    unittest.main()
