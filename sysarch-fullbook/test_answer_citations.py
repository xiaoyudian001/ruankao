import json
import unittest
from pathlib import Path

from answer_citations import normalize_citations
from answer_cleanup import clean_answer


def row(book=223, last=224, pdf=238, pdf_last=239, status='complete'):
    return {'source_file':'教材.pdf','chapter':'第6章数据库设计',
            'book_page_start':book,'book_page_end':last,'book_pages':','.join(map(str,range(book,last+1))),
            'pdf_page_start':pdf,'pdf_page_end':pdf_last,'pdf_pages':','.join(map(str,range(pdf,pdf_last+1))),
            'book_page_mapping_status':status}


class CitationTests(unittest.TestCase):
    def test_shortened_range_is_restored(self):
        result=normalize_citations('定义。[片段1，教材第223页（PDF第238页）]',[row()])
        self.assertEqual(result['text'],'定义。[片段1，教材第223～224页（PDF第238～239页），第6章数据库设计]')
        self.assertEqual(result['invalid_ranks'],[])

    def test_model_book_pdf_confusion_is_ignored(self):
        r=row(book=4,last=4,pdf=18,pdf_last=19,status='partial')
        result=normalize_citations('[片段1，教材第18～19页（PDF第18～19页）]',[r])
        self.assertEqual(result['text'],'[片段1，原PDF第18～19页（物理页），第6章数据库设计]')

    def test_multiple_citations_one_bracket_and_range(self):
        result=normalize_citations('甲[片段2，错误页码；片段1，错误章节]乙[片段1～2]',[row(),row(308,308,323,323)])
        self.assertEqual(result['referenced_ranks'],[2,1])
        self.assertIn('教材第308页（PDF第323页）',result['text'])
        self.assertEqual(result['text'].count('第6章数据库设计'),4)
        self.assertNotIn('错误',result['text'])

    def test_unknown_rank_not_rebound_to_valid_source(self):
        result=normalize_citations('[片段99，教材第308页（PDF第323页）]',[row()])
        self.assertEqual(result['invalid_ranks'],[99])
        self.assertEqual(result['text'],'[引用未核验：片段99]')

    def test_no_page_does_not_use_preformatted_model_hint(self):
        result=normalize_citations('[片段1，教材第308页]',[{'source_hint':'教材第308页','rag_rank':99}])
        self.assertEqual(result['text'],'[片段1]')

    def test_inline_latex_and_links_remain_unchanged(self):
        body='$$MTTF = \\int_{0}^{\\infty} R(t)\\,dt$$\nA=MTBF/(MTBF+MTTR)\n[网页](https://example.com)'
        self.assertEqual(normalize_citations(body,[row()])['text'],body)

    def test_think_removed_before_citation_processing(self):
        s=clean_answer('<think>不展示[片段99]</think>结果[片段1]')
        result=normalize_citations(s,[row()])
        self.assertEqual(result['invalid_ranks'],[])
        self.assertNotIn('think',result['text'])

    def test_fullwidth_brackets_and_digits(self):
        result=normalize_citations('结果【片段１】',[row()])
        self.assertIn('[片段1，教材第223～224页',result['text'])

    def test_code_and_quoted_markers_not_treated_as_sources(self):
        s='示例 `array[片段1]`\n```text\n[片段1]\n```\n结论[片段1]'
        result=normalize_citations(s,[row()])
        self.assertIn('`array[片段1]`',result['text'])
        self.assertIn('```text\n[片段1]\n```',result['text'])
        self.assertEqual(result['text'].count('教材第'),1)

    def test_numbered_list_citation_and_plain_page_diagnostics(self):
        result=normalize_citations('对比[片段1、2]，另外教材第500页。',[row(),row()])
        self.assertEqual(result['referenced_ranks'],[1,2])
        self.assertEqual(result['unbound_page_mentions'],['教材第500页'])

    def test_real_citation_table_cells_and_parentheses(self):
        s='| 要点 | 引用 |\n| 定义 | 片段1，教材第223页 |\n另一个要点（片段1）。'
        result=normalize_citations(s,[row()])
        self.assertEqual(result['text'].count('教材第223～224页'),2)
        self.assertEqual(result['unbound_page_mentions'],[])
        self.assertIn('| 定义 | [片段1，',result['text'])

    def test_narrative_table_cell_not_discarded(self):
        s='| 片段1说明了用户视图 | 说明 |'
        self.assertEqual(normalize_citations(s,[row()])['text'],s)

    def test_actual_problem_cases(self):
        root=Path(r'F:\daily\output\sysarch-rag-evaluation\subquery-refined-20261009')
        expected={'Q08':'教材第307～308页（PDF第322～323页）',
                  'Q13':'教材第223～224页（PDF第238～239页）',
                  'Q15':'原PDF第18～19页（物理页）'}
        for qid,label in expected.items():
            q=json.loads((root/(qid+'.json')).read_text(encoding='utf-8'))
            with self.subTest(qid=qid):
                result=normalize_citations(q['answer'],q['retrieved_chunks'])
                self.assertIn(label,result['text'])
                self.assertEqual(result['invalid_ranks'],[])


if __name__=='__main__':unittest.main()
