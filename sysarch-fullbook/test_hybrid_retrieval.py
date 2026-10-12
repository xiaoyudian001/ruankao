import unittest

try:
    from hybrid_retrieval import BM25Index, fuse_rrf, tokenize
except ImportError:
    BM25Index = None
    fuse_rrf = None
    tokenize = None


def row(cid, text, **metadata):
    return {"chunk_id": cid, "content": text, "section_type": "body",
            "source_sha256": "test-book", "pdf_pages": "323", "book_pages": "308", **metadata}


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(BM25Index, "混合检索实现尚未创建")

    def test_terms_and_layout(self):
        terms = tokenize("系统 架构 MTTR System Architecture 1.1.1 ＭＴＴＦ")
        self.assertIn("系统", terms)
        self.assertIn("统架", terms)
        self.assertIn("mttr", terms)
        self.assertIn("mttf", terms)
        self.assertIn("system", terms)
        self.assertIn("architecture", terms)
        self.assertIn("1.1.1", terms)

    def test_bm25_exact_term_and_source(self):
        index = BM25Index([row("a", "网络系统可用性"), row("b", "MTTR是平均恢复前时间")])
        result = index.search("mttr", 20)
        self.assertEqual([x["chunk_id"] for x in result], ["b"])
        self.assertGreater(result[0]["bm25_score"], 0)
        self.assertEqual(result[0]["book_pages"], "308")

    def test_empty_lexical_fallback(self):
        index = BM25Index([row("a", "MTTR恢复时间")])
        self.assertEqual(index.search("qzxy999", 20), [])
        result = fuse_rrf([row("a", "MTTR恢复时间")], [], 5)
        self.assertEqual(result[0]["dense_rank"], 1)
        self.assertIsNone(result[0]["lexical_rank"])

    def test_rrf_uses_ranks_not_raw_scores(self):
        a, b, c = row("a", "a"), row("b", "b"), row("c", "c")
        a["_score"] = 1e9
        b["bm25_score"] = .0001
        result = fuse_rrf([a, b], [c, b], 3)
        self.assertEqual(result[0]["chunk_id"], "b")
        self.assertAlmostEqual(result[0]["rrf_score"], 2 / 62)

    def test_duplicates_do_not_double_vote(self):
        a, b = row("a", "a"), row("b", "b")
        result = fuse_rrf([a, a, b], [b, b], 5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["chunk_id"], "b")
        self.assertEqual(result[0]["dense_rank"], 2)
        self.assertEqual(result[0]["lexical_rank"], 1)

    def test_conflicting_source_is_rejected(self):
        with self.assertRaises(ValueError):
            fuse_rrf([row("a", "original")], [row("a", "different")], 5)
        with self.assertRaises(ValueError):
            fuse_rrf([row("a", "original")], [row("a", "original", pdf_pages="324")], 5)

    def test_non_body_and_empty_query_rejected(self):
        with self.assertRaises(ValueError):
            BM25Index([row("a", "cover", section_type="front_matter")])
        index = BM25Index([row("a", "text")])
        with self.assertRaises(ValueError):
            index.search(" ", 5)


if __name__ == "__main__":
    unittest.main()
