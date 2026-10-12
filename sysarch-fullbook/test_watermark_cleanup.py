import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(r'F:\daily\output\sysarch-fullbook-v2')


class WatermarkCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import watermark_cleanup
        except ModuleNotFoundError:
            raise AssertionError('watermark_cleanup module is missing')
        cls.clean = staticmethod(watermark_cleanup.clean_markdown)

    def test_preserves_section_title_embedded_in_watermark(self):
        original = '文老师系统架构设计师\n\n上篇文老师系统架构设计师\n\n淘宝搜索'
        self.assertEqual(self.clean(16, original), '上篇')
        original = '：文老师系统架构设计师\n\n下篇淘宝搜索：文老师系统架构设计师'
        self.assertEqual(self.clean(418, original), '下篇')

    def test_removes_watermark_without_removing_adjacent_body(self):
        original = (ROOT / 'pages' / 'page_0038.md').read_text(encoding='utf-8')
        cleaned = self.clean(38, original)
        self.assertIn('Docker创造了容器化的技术潮流', cleaned)
        self.assertIn('系统架构设计师的成长', cleaned)
        self.assertNotIn('淘宝搜索', cleaned)
        self.assertNotIn('文老师', cleaned)

    def test_preserves_legitimate_figure_text_and_limits_scope(self):
        original = (ROOT / 'pages' / 'page_0647.md').read_text(encoding='utf-8')
        cleaned = self.clean(647, original)
        self.assertIn('图17-24 基于 5G网络的智能电网架构', cleaned)
        self.assertIn('系统架构设计师教程（第2版）', cleaned)
        self.assertNotIn('宝搜索', cleaned)
        self.assertEqual(self.clean(648, '淘宝搜索：文老师系统架构设计师'),
                         '淘宝搜索：文老师系统架构设计师')

    def test_only_verified_pages_change(self):
        from watermark_cleanup import clean_stored_chunk
        chunks = json.loads((ROOT / 'final_chunks.json').read_text(encoding='utf-8'))
        before = [row['content'] for row in chunks]
        after = [clean_stored_chunk(row) for row in chunks]
        changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(len(changed), 10)
        self.assertTrue(all(after[i].strip() for i in changed))
        self.assertTrue(all('淘宝搜索' not in after[i] and '文老师' not in after[i]
                            and '宝搜索' not in after[i] for i in changed))
        self.assertEqual(before[100], after[100])

    def test_derives_a_separate_version_with_source_metadata(self):
        from watermark_cleanup import build_corpus
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'v2'
            target = Path(temporary) / 'v3'
            (source / 'pages').mkdir(parents=True)
            original = '正文\n\n淘宝搜索：文老\n\n宝搜索：文老师系统架构设计师'
            (source / 'pages' / 'page_0119.md').write_text(original, encoding='utf-8')
            (source / 'pages' / 'page_0119.raw.md').write_text(original, encoding='utf-8')
            row = {'id': 'stored-id', 'content': original, 'char_count': len(original),
                   'metadata': {'pdf_pages': '119', 'pdf_page_start': '119',
                                'pdf_page_end': '119', 'section_type': 'body',
                                'chunk_id': 'old-chunk', '_id': 'old-id',
                                'processing_version': 'sysarch-v2-700-100-1',
                                'source_metadata': '{"chunk_id":"old-chunk"}'}}
            (source / 'final_chunks.json').write_text(json.dumps([row]), encoding='utf-8')
            report = build_corpus(source, target)
            cleaned = json.loads((target / 'final_chunks.json').read_text(encoding='utf-8'))[0]
            self.assertEqual(report['changed_chunks'], 1)
            self.assertEqual(report['changed_pages'], [119])
            self.assertEqual(cleaned['content'], '正文')
            self.assertEqual(cleaned['metadata']['pdf_pages'], '119')
            self.assertNotEqual(cleaned['metadata']['chunk_id'], 'old-chunk')
            self.assertEqual(json.loads(cleaned['metadata']['source_metadata'])['chunk_id'],
                             cleaned['metadata']['chunk_id'])
            self.assertEqual((source / 'pages' / 'page_0119.md').read_text(encoding='utf-8'), original)


if __name__ == '__main__':
    unittest.main()
