import unittest
from _loader import load_lore

lore = load_lore()


class TestFrontmatter(unittest.TestCase):
    def test_valid_subset(self):
        text = ("---\nname: alpha\ndescription: first\nmetadata:\n"
                "  type: project\n  originSessionId: sess-1\n---\n\nBody here.\n")
        meta, body, warn = lore.parse_frontmatter(text)
        self.assertEqual(meta["name"], "alpha")
        self.assertEqual(meta["description"], "first")
        self.assertEqual(meta["type"], "project")
        self.assertEqual(meta["originSessionId"], "sess-1")
        self.assertEqual(body, "Body here.\n")
        self.assertIsNone(warn)

    def test_absent(self):
        text = "# Heading\n\nNo frontmatter.\n"
        meta, body, warn = lore.parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)
        self.assertIsNone(warn)

    def test_unterminated(self):
        text = "---\nname: x\ndescription: y\n\nbody, no close\n"
        meta, body, warn = lore.parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)  # full text preserved as body
        self.assertEqual(warn, "unterminated frontmatter")

    def test_unknown_keys_ignored_silently(self):
        # Frontmatter shape varies; extra keys must not warn (real-world memories
        # carry tags/created/etc.). We extract what we know and ignore the rest.
        text = "---\nfoo: bar\nname: x\ntags:\n  - a\n  - b\n---\nbody\n"
        meta, _, warn = lore.parse_frontmatter(text)
        self.assertEqual(meta["name"], "x")
        self.assertIsNone(warn)
        self.assertNotIn("foo", meta)

    def test_type_at_top_level(self):
        # The cause of the field reports: older memories put `type:` at top level,
        # not under `metadata:`. It must still be captured.
        meta, _, warn = lore.parse_frontmatter("---\nname: x\ntype: feedback\n---\nb\n")
        self.assertEqual(meta["type"], "feedback")
        self.assertIsNone(warn)

    def test_title_alias_for_name(self):
        meta, _, _ = lore.parse_frontmatter("---\ntitle: Hello\n---\nb\n")
        self.assertEqual(meta["name"], "Hello")

    def test_quoted_values_unquoted(self):
        meta, _, _ = lore.parse_frontmatter('---\nname: "quoted"\n---\nb\n')
        self.assertEqual(meta["name"], "quoted")

    def test_metadata_nested_type_and_extra_child(self):
        text = "---\nname: x\nmetadata:\n  node_type: memory\n  type: user\n---\nb\n"
        meta, _, warn = lore.parse_frontmatter(text)
        self.assertEqual(meta["type"], "user")
        self.assertNotIn("node_type", meta)
        self.assertIsNone(warn)


if __name__ == "__main__":
    unittest.main()
