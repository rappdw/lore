"""v0b — the token-overlap scorer (offline, deterministic) and the opt-in LLM
commands (summarize/relevant) driven by an injected stub model (no real LLM)."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock
from _loader import load_lore, build_fixture, run, args_ns

lore = load_lore()


class TestScorer(unittest.TestCase):
    """Deterministic, no LLM — the shared primitive curation will reuse."""

    def test_tokenize_drops_stopwords_and_singletons(self):
        toks = lore.tokenize("The quick brown fox a I")
        self.assertNotIn("the", toks)          # stopword
        self.assertNotIn("a", toks)            # 1-char
        self.assertNotIn("i", toks)            # 1-char
        self.assertEqual(toks, ["quick", "brown", "fox"])

    def test_shingles_are_ngrams(self):
        sh = lore.shingles("alpha beta gamma delta")
        self.assertIn(("alpha", "beta"), sh)            # 2-gram
        self.assertIn(("alpha", "beta", "gamma"), sh)   # 3-gram
        self.assertNotIn(("alpha",), sh)                # no unigrams when n>=2 fits

    def test_shingles_unigram_fallback_for_tiny_text(self):
        # One content token can't form a 2-gram → fall back to unigrams so it scores.
        sh = lore.shingles("alpha the of")
        self.assertEqual(sh, {("alpha",)})

    def test_shingles_empty(self):
        self.assertEqual(lore.shingles(""), set())
        self.assertEqual(lore.shingles("the of and"), set())  # all stopwords

    def test_jaccard_bounds(self):
        a = lore.shingles("alpha beta gamma")
        self.assertEqual(lore.jaccard(a, a), 1.0)              # identical
        self.assertEqual(lore.jaccard(a, lore.shingles("xx yy zz")), 0.0)  # disjoint
        self.assertEqual(lore.jaccard(set(), set()), 0.0)      # both empty
        # symmetric
        b = lore.shingles("alpha beta delta")
        self.assertEqual(lore.jaccard(a, b), lore.jaccard(b, a))
        self.assertTrue(0.0 < lore.jaccard(a, b) < 1.0)        # partial overlap

    def _item(self, title, body, slug="p", desc=None):
        return lore.MemoryItem(
            agent="claude", source="sandbox:t", source_kind="auto_memory",
            project=slug, project_slug=slug, path="/%s.md" % title,
            title=title, body=body, mtime=0.0, description=desc)

    def test_rank_relevant_picks_overlap(self):
        target = [self._item("auth", "token refresh oauth login session flow", "app")]
        cands = [
            self._item("oauth-notes", "oauth token refresh and login session", "lib"),
            self._item("css", "flexbox grid layout padding margins", "lib"),
        ]
        ranked = lore.rank_relevant(target, cands, top_n=10)
        self.assertEqual(ranked[0][0].title, "oauth-notes")
        self.assertTrue(ranked[0][1] > 0)
        # The unrelated css note scores zero and is dropped.
        self.assertTrue(all(it.title != "css" for it, _ in ranked))

    def test_rank_relevant_respects_top_n_and_empty_target(self):
        target = [self._item("x", "alpha beta gamma delta epsilon", "app")]
        cands = [self._item("c%d" % i, "alpha beta gamma delta", "lib") for i in range(5)]
        self.assertEqual(len(lore.rank_relevant(target, cands, top_n=2)), 2)
        # Empty/contentless target → nothing to compare against.
        self.assertEqual(lore.rank_relevant([], cands, top_n=5), [])


class _LLMTest(unittest.TestCase):
    """Base: fixture + an injected stub model that records its calls."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lore-llm-")
        cls.root = os.path.join(build_fixture(cls.tmp), "sandboxes")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.calls = []

        def stub(prompt, model):
            self.calls.append((prompt, model))
            return "STUB-SUMMARY"
        lore.LLM_RUNNER = stub

    def tearDown(self):
        lore.LLM_RUNNER = None

    def lore(self, *argv):
        return run(lore, list(argv) + ["--sandboxes-root", self.root])


class TestSummarize(_LLMTest):
    def test_single_chunk_one_call(self):
        code, out, _ = self.lore("summarize")
        self.assertEqual(code, 0)
        self.assertIn("STUB-SUMMARY", out)
        self.assertEqual(len(self.calls), 1)              # under budget → one call

    def test_json_shape(self):
        code, out, _ = self.lore("summarize", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["summary"], "STUB-SUMMARY")
        self.assertGreater(d["items"], 0)
        self.assertIn("chunks", d)

    def test_model_flag_threaded_through(self):
        self.lore("summarize", "--model", "claude-opus-4-8")
        self.assertEqual(self.calls[0][1], "claude-opus-4-8")

    def test_map_reduce_over_budget(self):
        # Shrink the budget so each memory becomes its own chunk → map then reduce.
        saved = lore.SUMMARIZE_CHAR_BUDGET
        lore.SUMMARIZE_CHAR_BUDGET = 10
        try:
            code, out, _ = self.lore("summarize", "--json")
            self.assertEqual(code, 0)
            d = json.loads(out)
            self.assertGreater(d["chunks"], 1)
            # one call per chunk (map) + one reduce call
            self.assertEqual(len(self.calls), d["chunks"] + 1)
        finally:
            lore.SUMMARIZE_CHAR_BUDGET = saved

    def test_empty_selection_no_llm(self):
        # A known agent with no adapter yields nothing → friendly exit, no LLM call.
        code, out, _ = self.lore("summarize", "--agent", "gemini")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to summarize", out)
        self.assertEqual(len(self.calls), 0)

    def test_no_credentials_exits_1(self):
        lore.LLM_RUNNER = None
        empty = tempfile.mkdtemp(prefix="lore-nokey-")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
            code, _, err = run(lore, ["summarize", "--sandboxes-root", self.root,
                                      "--sandy-home", empty])
        shutil.rmtree(empty, ignore_errors=True)
        self.assertEqual(code, 1)
        self.assertIn("ANTHROPIC_API_KEY", err)


class TestRelevant(_LLMTest):
    def test_offline_ranked_list_no_llm(self):
        # Without --explain, relevant is a pure scorer — must NOT call the LLM.
        code, out, _ = self.lore("relevant", "zork", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["project"], "zork")
        self.assertIsNone(d["explanation"])
        self.assertEqual(len(self.calls), 0)
        # candidates come from OTHER projects only
        for c in d["candidates"]:
            self.assertNotEqual(c["project_slug"], "-Users-x-dev-zork")

    def test_unknown_project_exits_1(self):
        code, _, err = self.lore("relevant", "no-such-project")
        self.assertEqual(code, 1)
        self.assertIn("no memories", err)

    def test_top_n_caps_candidates(self):
        code, out, _ = self.lore("relevant", "zork", "--top", "1", "--json")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(json.loads(out)["candidates"]), 1)

    def test_explain_invokes_llm(self):
        code, out, _ = self.lore("relevant", "zork", "--explain", "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        if d["count"]:                       # only ranks → explains when there are hits
            self.assertEqual(d["explanation"], "STUB-SUMMARY")
            self.assertEqual(len(self.calls), 1)

    def test_explain_without_credentials_exits_1(self):
        lore.LLM_RUNNER = None
        empty = tempfile.mkdtemp(prefix="lore-nokey-")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
            code, _, err = run(lore, ["relevant", "zork", "--explain",
                                      "--sandboxes-root", self.root,
                                      "--sandy-home", empty])
        shutil.rmtree(empty, ignore_errors=True)
        # If there were candidates, --explain needs a credential → exit 1.
        self.assertIn(code, (0, 1))
        if code == 1:
            self.assertIn("ANTHROPIC_API_KEY", err)


class TestCredentials(unittest.TestCase):
    """Credential resolution: env first, then $SANDY_HOME/{.secrets,config}."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lore-cred-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _no_env(self):
        ctx = mock.patch.dict(os.environ, {}, clear=False)
        ctx.start()
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        self.addCleanup(ctx.stop)

    def _write(self, name, content):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as f:
            f.write(content)

    def test_env_api_key_wins(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env"}):
            self.assertEqual(lore._auth_headers(args_ns()), {"x-api-key": "sk-env"})

    def test_secrets_file_api_key(self):
        self._no_env()
        self._write(".secrets", "# creds\nANTHROPIC_API_KEY=sk-file\nGEMINI_API_KEY=g\n")
        self.assertEqual(lore._auth_headers(args_ns(sandy_home=self.tmp)),
                         {"x-api-key": "sk-file"})

    def test_oauth_token_is_not_accepted(self):
        # A Claude Code subscription OAuth token must NOT authenticate the API —
        # routing it to /v1/messages is a ToS violation (enforced). Token alone → None.
        self._no_env()
        self._write(".secrets", 'export CLAUDE_CODE_OAUTH_TOKEN="tok-1"\n')
        self.assertIsNone(lore._auth_headers(args_ns(sandy_home=self.tmp)))

    def test_oauth_token_ignored_when_api_key_present(self):
        self._no_env()
        self._write(".secrets", "CLAUDE_CODE_OAUTH_TOKEN=tok\nANTHROPIC_API_KEY=sk-x\n")
        self.assertEqual(lore._auth_headers(args_ns(sandy_home=self.tmp)),
                         {"x-api-key": "sk-x"})

    def test_no_credential_returns_none(self):
        self._no_env()
        self.assertIsNone(lore._auth_headers(args_ns(sandy_home=self.tmp)))


if __name__ == "__main__":
    unittest.main()
