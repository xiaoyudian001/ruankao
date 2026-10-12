import json
import tempfile
import unittest
from pathlib import Path
from core import clean_text, make_chunks, stable_chunk_id, save_json_atomic

class CoreTests(unittest.TestCase):
    def test_cleanup_preserves_english_numbers_and_paragraphs(self):
        self.assertEqual(clean_text('系统 架构\n设计师 ENIAC 84%\n\n## 1.1 标题'),
                         '系统架构设计师 ENIAC 84%\n\n## 1.1 标题')

    def test_ids_are_stable_and_page_specific(self):
        first = stable_chunk_id('abc', 'body', 0, [18], '同一段文字')
        self.assertIsInstance(first, str)
        self.assertEqual(first, stable_chunk_id('abc', 'body', 0, [18], '同一段文字'))
        self.assertNotEqual(first, stable_chunk_id('abc', 'body', 0, [19], '同一段文字'))

    def test_cross_page_continuation_keeps_both_source_pages(self):
        rows, state = make_chunks({}, [{'page':18,'text':'需要具有跨学','chapter':'第1章'},
                                       {'page':19,'text':'科能力和整体设计能力。','chapter':'第1章'}],
                                  'abc','book.pdf','body',final=True)
        self.assertEqual(len(rows),1)
        self.assertIn('跨学科',rows[0]['text'])
        self.assertEqual(rows[0]['pdf_pages'],'18,19')
        self.assertEqual((rows[0]['pdf_page_start'],rows[0]['pdf_page_end']),(18,19))

    def test_resume_matches_uninterrupted_and_keeps_overlap(self):
        a={'page':21,'text':'甲'*850,'chapter':'第1章'}
        b={'page':22,'text':'乙'*800,'chapter':'第1章'}
        whole,_=make_chunks({},[a,b],'abc','book.pdf','body',final=True)
        first,state=make_chunks({},[a],'abc','book.pdf','body')
        resumed,_=make_chunks(json.loads(json.dumps(state)),[b],'abc','book.pdf','body',final=True)
        self.assertEqual(whole,first+resumed)
        self.assertGreaterEqual(len(whole),3)
        self.assertTrue(all(0<len(r['text'])<=700 for r in whole))
        self.assertEqual(whole[0]['text'][-100:],whole[1]['text'][:100])
        self.assertTrue(any(r['pdf_pages']=='21,22' for r in whole))

    def test_headings_do_not_get_joined_across_pages(self):
        rows,_=make_chunks({},[{'page':21,'text':'段落结尾。','chapter':'第1章'},
                              {'page':22,'text':'## 第2章 新标题\n\n新的正文。','chapter':'第2章'}],
                           'abc','book.pdf','body',final=True)
        self.assertEqual(len(rows),1)
        self.assertIn('。\n\n## 第2章',rows[0]['text'])

    def test_atomic_state_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'progress.json'
            save_json_atomic(p,{'done':[18,19]})
            self.assertTrue(p.exists())
            self.assertEqual(json.loads(p.read_text(encoding='utf-8')),{'done':[18,19]})

    def test_portable_metadata_can_filter_body_and_chunk(self):
        rows,_=make_chunks({},[{'page':18,'text':'测试正文。','chapter':'第1章'}],'abc','book.pdf','body',final=True)
        self.assertIn('source_metadata',rows[0])
        tags=json.loads(rows[0]['source_metadata'])
        self.assertEqual(tags['section_type'],'body')
        self.assertEqual(tags['chunk_id'],rows[0]['chunk_id'])

if __name__=='__main__':
    unittest.main()
