import unittest
from _loader import load_lore

lore = load_lore()


class TestWikilinks(unittest.TestCase):
    def test_basic_and_alias(self):
        self.assertEqual(lore.extract_wikilinks("see [[alpha]] and [[beta|the beta]]"),
                         ["alpha", "beta"])

    def test_dedup_preserves_order(self):
        self.assertEqual(lore.extract_wikilinks("[[b]] [[a]] [[b]] [[a]]"), ["b", "a"])

    def test_code_fence_ignored(self):
        text = "real [[x]]\n```\nfenced [[y]]\n```\nafter [[z]]\n"
        self.assertEqual(lore.extract_wikilinks(text), ["x", "z"])

    def test_none(self):
        self.assertEqual(lore.extract_wikilinks("no links here"), [])


if __name__ == "__main__":
    unittest.main()
