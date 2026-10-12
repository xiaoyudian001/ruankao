import unittest

try:
    from parent_context import BOOK_SHA, build_parent_index, expand_context
except ImportError:
    BOOK_SHA = 'a'*64
    build_parent_index = expand_context = None


def row(i, text, chapter='第1章', page=20):
    return {'chunk_id':f'{i:064x}', 'source_sha256':BOOK_SHA, 'content':text,
            'section_type':'body', 'chapter':chapter, 'pdf_pages':str(page),
            'pdf_page_start':str(page), 'pdf_page_end':str(page)}


class ParentContextTest(unittest.TestCase):
    def test_feature_exists(self):
        self.assertIsNotNone(expand_context, 'Parent context expansion is not implemented')

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_hit_rank_and_actual_sources_are_preserved(self):
        corpus=[row(1,'## 1.1 定义\n定义前半段。'),row(2,'定义后半段和适用条件。'),row(3,'同节说明。')]
        result, trace=expand_context([corpus[1]],build_parent_index(corpus))
        self.assertEqual(result[0]['chunk_id'],corpus[1]['chunk_id'])
        self.assertEqual([r['rag_rank'] for r in result],[1,2,3])
        self.assertEqual({r['chunk_id'] for r in result},{r['chunk_id'] for r in corpus})
        for r in result:
            original=next(s for s in corpus if s['chunk_id']==r['chunk_id'])
            self.assertEqual(r['content'],original['content'])
            self.assertEqual(r['pdf_pages'],original['pdf_pages'])
        self.assertEqual(trace['added_count'],2)
        self.assertEqual(result[1]['context_hit_ranks'],[1])

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_new_heading_and_chapter_are_boundaries(self):
        corpus=[row(1,'## 1.1 甲\n甲内容。'),row(2,'甲的续文。'),row(3,'## 1.2 乙\n乙内容。'),row(4,'下一章。','第2章')]
        expanded,_=expand_context([corpus[1]],build_parent_index(corpus))
        self.assertEqual({r['chunk_id'] for r in expanded},{corpus[0]['chunk_id'],corpus[1]['chunk_id']})
        expanded,_=expand_context([corpus[2]],build_parent_index(corpus))
        self.assertEqual(len(expanded),1)

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_two_hits_share_context_without_duplicate_sources(self):
        corpus=[row(1,'## 1.1 甲\n前。'),row(2,'中。'),row(3,'后。'),row(4,'末。')]
        expanded,_=expand_context([corpus[0],corpus[2]],build_parent_index(corpus))
        self.assertEqual([r['chunk_id'] for r in expanded[:2]],[corpus[0]['chunk_id'],corpus[2]['chunk_id']])
        middle=next(r for r in expanded if r['chunk_id']==corpus[1]['chunk_id'])
        self.assertEqual(middle['context_hit_ranks'],[1,2])
        self.assertEqual(len({r['chunk_id'] for r in expanded}),len(expanded))

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_budget_excludes_whole_neighbor_without_truncating_hit(self):
        corpus=[row(1,'## 1.1 甲\n'+'长'*700),row(2,'定义。'),row(3,'后文。')]
        expanded,trace=expand_context([corpus[1]],build_parent_index(corpus),max_chars=300)
        self.assertEqual(expanded[0]['content'],'定义。')
        self.assertNotIn(corpus[0]['chunk_id'],[r['chunk_id'] for r in expanded])
        self.assertLessEqual(trace['context_chars'],300)
        expanded,_=expand_context([corpus[1]],build_parent_index(corpus),max_rows=1)
        self.assertEqual(len(expanded),1)

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_changed_text_or_unknown_child_cannot_be_expanded(self):
        corpus=[row(1,'定义。'),row(2,'续文。')]
        for hit in [row(99,'未知。'),{**corpus[0],'content':'另一本书。'}, {**corpus[0],'source_sha256':'b'*64}]:
            with self.subTest(hit=hit['chunk_id']):
                with self.assertRaises(ValueError):
                    expand_context([hit],build_parent_index(corpus))

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_empty_retrieval_does_not_fetch_context(self):
        expanded,trace=expand_context([],build_parent_index([row(1,'正文。')]))
        self.assertEqual(expanded,[])
        self.assertEqual(trace['added_count'],0)

    @unittest.skipIf(expand_context is None, 'Feature not implemented')
    def test_shared_parent_does_not_overwrite_each_child_heading(self):
        corpus=[row(1,'## 1.1 甲\n甲。\n## 1.2 乙\n乙的开始。'),row(2,'乙的续文。')]
        index=build_parent_index(corpus)
        expanded,_=expand_context([corpus[0]],index)
        self.assertIn('1.1 甲',expanded[0]['context_title'])
        self.assertIn('1.2 乙',expanded[0]['context_title'])
        self.assertEqual(expanded[1]['context_title'],'1.2 乙')


if __name__=='__main__':
    unittest.main()
