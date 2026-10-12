import copy
import unittest
from complete_retrieval import coverage_select
from complete_retrieval import comparison_fallback


def row(cid, query):
    return {'chunk_id': cid, 'content': '原文'+cid, 'chapter': '第9章', 'source_hint': '教材308/PDF323',
            'book_pages': '308', 'pdf_pages': '323', 'matched_queries': [query],
            'section_type':'body','source_sha256':'pdfsha'}


class CompleteRetrievalTest(unittest.TestCase):
    def test_extract_pair_only_when_no_substantive_constraints_are_lost(self):
        plan=comparison_fallback('结构模型与框架模型有什么区别？依据教材比较描述重点。','model_invalid')
        self.assertEqual(plan['route'],'split')
        self.assertEqual([q['query'] for q in plan['queries']],['结构模型的描述重点是什么？','框架模型的描述重点是什么？'])
        # Do not guess how extra requirements bind to each object.
        for question in ('结合甲和乙说明系统的设计原则','甲与乙有什么区别？请列出适用条件和性能指标。','第9章甲与乙有什么区别？'):
            plan=comparison_fallback(question,'model_invalid')
            self.assertEqual(plan['route'],'direct')

    def test_identical_scoped_query_text_keeps_distinct_chapter_coverage(self):
        rows=[{**row('nine','same'),'coverage_labels':['same@9']},
              {**row('17a','same'),'coverage_labels':['same@17']},
              {**row('17b','same'),'coverage_labels':['same@17']}]
        result=coverage_select(rows,[-1,10,8],['same@9','same@17'],2)
        self.assertEqual({r['chunk_id'] for r in result},{'nine','17a'})

    def test_low_score_second_topic_survives_global_top_five(self):
        rows = [row(str(i), 'A') for i in range(5)] + [row('B', 'B')]
        before = copy.deepcopy(rows)
        result = coverage_select(rows, [10,9,8,7,6,-3], ['A','B'])
        self.assertEqual(len(result),5)
        self.assertIn('B',[r['chunk_id'] for r in result])
        self.assertEqual(rows,before)
        self.assertEqual([r['rag_rank'] for r in result],[1,2,3,4,5])
        for r in result:
            original=next(x for x in rows if x['chunk_id']==r['chunk_id'])
            for key in ('content','chapter','source_hint','book_pages','pdf_pages'):
                self.assertEqual(r[key],original[key])

    def test_shared_evidence_counts_for_two_queries(self):
        rows=[{**row('shared','A'),'matched_queries':['A','B']},row('a','A'),row('b','B')]
        result=coverage_select(rows,[10,8,7],['A','B'],final_k=2)
        self.assertEqual([r['chunk_id'] for r in result],['shared','a'])

    def test_fallback_still_covers_each_available_topic(self):
        result=coverage_select([row('a','A'),row('a2','A'),row('b','B')],None,['A','B'],2)
        self.assertEqual([r['chunk_id'] for r in result],['a','b'])
        self.assertTrue(all(r['rerank_score'] is None for r in result))

    def test_missing_topic_not_fabricated(self):
        result=coverage_select([row('a','A')],[1],['A','B'])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['matched_queries'],['A'])

    def test_bad_scores_duplicates_and_untrusted_labels_rejected(self):
        for scores in ([True],[float('nan')],[],[1,2]):
            with self.assertRaises(ValueError):coverage_select([row('a','A')],scores,['A'])
        with self.assertRaises(ValueError):coverage_select([row('a','A'),row('a','A')],[1,2],['A'])
        with self.assertRaises(ValueError):coverage_select([row('a','fake')],[1],['A'])


if __name__=='__main__':unittest.main()
