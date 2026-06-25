"""`menu` — the stdlib interactive command picker. Driven by feeding answers to
a patched `input`; asserts it lists commands, dispatches, and inherits context."""
import os
import shutil
import tempfile
import unittest
from unittest import mock
from _loader import load_lore, build_fixture, run

lore = load_lore()


class TestMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-menu-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _menu(self, answers, *extra):
        with mock.patch("builtins.input", side_effect=list(answers)):
            return run(lore, ["menu", "--sandboxes-root", self.root, *extra])

    def test_lists_commands_then_empty_exits(self):
        code, out, _ = self._menu([""])          # empty choice → clean exit
        self.assertEqual(code, 0)
        self.assertIn("pick a command", out)
        self.assertIn("summarize", out)
        self.assertIn("ls", out)
        self.assertNotIn("menu", out.split("running:")[0])  # menu hides itself

    def test_dispatch_by_name(self):
        code, out, _ = self._menu(["stats"])     # stats has no command-specific opts
        self.assertEqual(code, 0)
        self.assertIn("running: lore stats", out)
        self.assertIn("by agent", out)           # stats actually ran

    def test_dispatch_by_number_runs_command(self):
        # 1) ls, then skip its three options (--type, --project, --sort).
        code, out, _ = self._menu(["1", "", "", ""])
        self.assertEqual(code, 0)
        self.assertIn("zork", out)               # ls ran against the fixture

    def test_positional_and_choice_option(self):
        # search <query>=alpha; opts in order: --type, --project, --field (title),
        # --memories-only, --sessions-only, --all (skip the flags).
        code, out, _ = self._menu(["search", "alpha", "", "", "title", "", "", ""])
        self.assertEqual(code, 0)
        self.assertIn("running: lore search alpha --field title", out)
        self.assertIn("alpha", out)

    def test_store_true_flag_yes(self):
        # graph options in order: --project (skip), --dot (y), --cross-project (skip).
        code, out, _ = self._menu(["graph", "", "y", ""])
        self.assertEqual(code, 0)
        self.assertIn("--dot", out)
        self.assertIn("digraph lore {", out)     # --dot took effect

    def test_invalid_choice_is_usage_error(self):
        code, _, err = self._menu(["nope"])
        self.assertEqual(code, 2)
        self.assertIn("not a valid choice", err)

    def test_cannot_recurse_into_menu(self):
        code, _, err = self._menu(["menu"])      # selecting menu by name is rejected
        self.assertEqual(code, 2)

    def test_inherits_sandboxes_root(self):
        code, out, _ = self._menu(["ls", "", "", ""])
        self.assertIn("--sandboxes-root", out)   # echoed into the dispatched argv


if __name__ == "__main__":
    unittest.main()
