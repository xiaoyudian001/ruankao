import copy
import json
import math
import unittest

try:
    from rerank_retrieval import apply_scores, fallback_rows, make_payload
except ImportError:
    apply_scores = fallback_rows = make_payload = None

try:
    from rerank_retrieval import apply_local_scores
except ImportError:
    apply_local_scores = None


def rows(n=6):
    return [{'chunk_id': str(i), 'content': '原文' + str(i), 'chapter': '第1章绪论',
             'source_sha256': 'pdfsha', 'section_type': 'body', 'pdf_pages': str(i + 15),
             'book_pages': str(i), 'rrf_score': 1/(60+i), 'rag_rank': i}
            for i in range(1, n+1)]


def scores(values):
    return json.dumps({'scores': [{'id': i, 'score': s} for i, s in enumerate(values, 1)]})


class RerankTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(apply_scores, '重排序实现尚未创建')

    def test_sort_preserves_source_and_input(self):
        original = rows(); saved = copy.deepcopy(original)
        out = apply_scores(original, scores([0, 1, 2, 3, 4, 4]), 3)
        self.assertEqual([r['chunk_id'] for r in out], ['5', '6', '4'])
        self.assertEqual([r['rag_rank'] for r in out], [1, 2, 3])
        for r in out:
            source = saved[int(r['chunk_id'])-1]
            for k in ('content', 'chapter', 'source_sha256', 'chunk_id', 'pdf_pages', 'book_pages'):
                self.assertEqual(r[k], source[k])
        self.assertEqual(original, saved)

    def test_ties_keep_rrf_order(self):
        self.assertEqual([r['chunk_id'] for r in apply_scores(rows(), scores([2]*6), 5)], ['1', '2', '3', '4', '5'])

    def test_missing_duplicate_or_out_of_range_id_rejected(self):
        for ids in ([1, 2], [1, 2, 3, 4, 5, 5], [1, 2, 3, 4, 5, 7], [True, 2, 3, 4, 5, 6]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                apply_scores(rows(), json.dumps({'scores': [{'id': i, 'score': 2} for i in ids]}))

    def test_invalid_scores_rejected(self):
        for s in (True, -1, 4.1, '3', math.nan, math.inf, None):
            with self.subTest(score=s), self.assertRaises(ValueError):
                apply_scores(rows(1), scores([s]))

    def test_extra_generated_content_rejected(self):
        with self.assertRaises(ValueError):
            apply_scores(rows(1), '{"scores":[{"id":1,"score":4,"content":"替换原文"}]}')

    def test_think_and_fence_not_exposed(self):
        out = apply_scores(rows(1), '<think>internal</think>\n```json\n' + scores([3]) + '\n```')
        self.assertEqual(out[0]['rerank_score'], 3)
        self.assertNotIn('internal', json.dumps(out))

    def test_fallback_keeps_original_top_five_and_ranks(self):
        out = fallback_rows(rows(), 5, 'TimeoutError')
        self.assertEqual([r['chunk_id'] for r in out], ['1', '2', '3', '4', '5'])
        self.assertTrue(all(r['rerank_method'] == 'rrf_fallback' for r in out))

    def test_payload_has_full_text_and_bounded_count(self):
        payload = json.loads(make_payload('我的问题', rows()))
        self.assertEqual(payload['question'], '我的问题')
        self.assertEqual(payload['candidates'][0]['text'], '原文1')
        with self.assertRaises(ValueError): make_payload('我的问题', rows(21))
        with self.assertRaises(ValueError): make_payload(' ', rows())

    def test_empty_and_short_candidates(self):
        self.assertEqual(fallback_rows([], 5, 'Empty'), [])
        self.assertEqual(apply_scores([], '{"scores":[]}'), [])
        self.assertEqual(len(apply_scores(rows(2), scores([0, 0]))), 2)

    def test_local_logits_are_not_probabilities_and_keep_sources(self):
        self.assertIsNotNone(apply_local_scores, '本地专用模型排序接口尚未实现')
        original = rows(3)
        out = apply_local_scores(original, [-12.5, 8.3, 8.3], 2)
        self.assertEqual([r['chunk_id'] for r in out], ['2', '3'])
        self.assertEqual(out[0]['rerank_score'], 8.3)
        self.assertEqual(out[0]['content'], original[1]['content'])
        self.assertEqual(out[0]['rerank_method'], 'local_cross_encoder')

    def test_local_score_count_and_nan_are_rejected(self):
        self.assertIsNotNone(apply_local_scores, '本地专用模型排序接口尚未实现')
        for values in ([1], [1, math.nan], [1, True]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                apply_local_scores(rows(2), values)


if __name__ == '__main__':
    unittest.main()
