import unittest
from citation_format import source_hint

class CitationTests(unittest.TestCase):
    def test_single_physical_page(self):
        text=source_hint({'source_file':'book.pdf','pdf_page_start':'26','pdf_page_end':'26','chapter':'第1章'})
        self.assertEqual(text,'来源：book.pdf；原PDF第26页（物理页）；第1章')

    def test_cross_page_range(self):
        self.assertEqual(source_hint({'source_file':'book.pdf','pdf_page_start':'25','pdf_page_end':'26'}),
                         '来源：book.pdf；原PDF第25～26页（物理页）')

    def test_legacy_chunks_do_not_gain_invented_pages(self):
        self.assertEqual(source_hint({'content':'旧片段'}),'')

    def test_invalid_pages_do_not_become_citations(self):
        self.assertEqual(source_hint({'source_file':'book.pdf','pdf_page_start':'30','pdf_page_end':'20'}),'')

if __name__=='__main__':
    unittest.main()
