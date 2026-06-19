import unittest
from _loader import load_lore

lore = load_lore()


class TestIndexParser(unittest.TestCase):
    def test_standard_line(self):
        entries = lore.parse_memory_index("- [Alpha](alpha.md) — the hook\n")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "Alpha")
        self.assertEqual(entries[0].slug, "alpha.md")
        self.assertEqual(entries[0].hook, "the hook")

    def test_separator_and_hook_variants(self):
        text = ("- [A](a.md) — em dash\n"
                "* [B](b.md) -- double hyphen\n"
                "+ [C](c.md)\n")  # no hook
        entries = lore.parse_memory_index(text)
        self.assertEqual([e.slug for e in entries], ["a.md", "b.md", "c.md"])
        self.assertEqual(entries[2].hook, None)

    def test_non_link_lines_ignored(self):
        text = "# Header\n\nSome prose.\n- [Real](real.md) — yes\nnot a bullet\n"
        entries = lore.parse_memory_index(text)
        self.assertEqual([e.slug for e in entries], ["real.md"])

    def test_target_normalized_to_basename(self):
        entries = lore.parse_memory_index("- [X](./sub/x.md) — h\n")
        self.assertEqual(entries[0].slug, "x.md")


if __name__ == "__main__":
    unittest.main()
