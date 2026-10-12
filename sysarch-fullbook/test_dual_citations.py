import unittest
from citation_format import source_hint

class DualCitationTests(unittest.TestCase):
    def row(self, **kwargs):
        return dict(source_file='book.pdf', pdf_page_start='323', pdf_page_end='323',
                    book_page_start='308', book_page_end='308', book_pages='308',
                    book_page_mapping_status='complete', **kwargs)

    def test_single_printed_page(self):
        self.assertEqual(source_hint(self.row()), '来源：book.pdf；教材第308页（PDF第323页）')

    def test_cross_page_range(self):
        row=self.row();row.update(pdf_page_start='322',book_page_start='307',book_pages='307,308')
        self.assertEqual(source_hint(row), '来源：book.pdf；教材第307～308页（PDF第322～323页）')

    def test_incomplete_mapping_falls_back_to_pdf(self):
        row=self.row();row.update(book_page_mapping_status='partial')
        self.assertEqual(source_hint(row), '来源：book.pdf；原PDF第323页（物理页）')

    def test_no_implicit_minus_15_for_unknown_books(self):
        self.assertEqual(source_hint({'source_file':'other.pdf','pdf_page_start':'323','pdf_page_end':'323'}),
                         '来源：other.pdf；原PDF第323页（物理页）')

    def test_invalid_book_range_falls_back(self):
        row=self.row();row.update(book_page_start='309')
        self.assertEqual(source_hint(row), '来源：book.pdf；原PDF第323页（物理页）')

    def test_book_range_requires_complete_consistent_list(self):
        row=self.row();row.update(pdf_page_end='324',book_page_end='309',book_pages='308')
        self.assertEqual(source_hint(row), '来源：book.pdf；原PDF第323～324页（物理页）')

if __name__=='__main__': unittest.main()
