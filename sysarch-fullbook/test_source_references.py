import unittest
import source_references as sources
from citation_format import source_hint
sources.source_hint = source_hint


class SourceSnapshotTest(unittest.TestCase):
    def row(self, **changes):
        return dict(source_sha256=sources.BOOK_SHA, pdf_page_start='323', pdf_page_end='323',
                    content='原始检索文本', chunk_id='a'*64, chapter='第9章', **changes)

    def test_actual_row_rank_is_not_compressed(self):
        refs = sources.source_references([{'source_sha256':'other'}, self.row()])
        self.assertEqual(refs[0]['rank'], 2)
        self.assertEqual(refs[0]['content'], '原始检索文本')
        self.assertEqual(refs[0]['pdfPages'], [323])

    def test_no_unknown_book_or_unbounded_page_range(self):
        for row in [{'source_sha256':'other'}, {**self.row(), 'pdf_page_end':'729'},
                    {**self.row(), 'pdf_page_end':'330'}, {**self.row(), 'content':''}]:
            self.assertEqual(sources.source_references([row]), [])


if __name__ == '__main__':
    unittest.main()
