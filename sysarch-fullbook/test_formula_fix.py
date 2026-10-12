import ast
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(r'F:\daily\output\sysarch-formula-fix')
CORPUS=Path(r'F:\daily\output\sysarch-fullbook-v3-watermark\final_chunks.json')

def load_functions(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Assign)) or isinstance(n,ast.Import) and all(x.name in ('re','copy') for x in n.names)]
    namespace={}
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),namespace)
    return namespace

def functions():
    helper=Path(__file__).with_name('formula_evidence.py')
    cleaner=Path(__file__).with_name('answer_cleanup.py')
    evidence=load_functions(helper) if helper.exists() else {}
    cleanup=load_functions(cleaner) if cleaner.exists() else load_functions(ROOT/'cleaner-before.py')
    return evidence.get('enrich_formula_evidence',lambda row:copy.deepcopy(row)),cleanup.get('clean_answer',cleanup.get('strip_think'))

class FormulaFixTests(unittest.TestCase):
    def setUp(self):
        rows=json.loads(CORPUS.read_text(encoding='utf-8'))
        r=next(r for r in rows if r['id'].startswith('22dcb120b49f'))
        self.row={**r['metadata'],'content':r['content']}
        self.enrich,self.clean=functions()

    def test_verified_page_restores_relation_and_definitions(self):
        updated=self.enrich(self.row)
        self.assertIn('MTBF = MTTF + MTTR',updated['content'])
        self.assertIn('Mean Time To Restoration',updated['content'])
        self.assertIn(r'\int_{0}^{\infty} R(t)',updated['content'])
        self.assertIn('可靠度服从指数分布',updated['content'])

    def test_another_source_or_page_is_unchanged(self):
        for key,value in [('source_sha256','other-book'),('chunk_id','unreviewed-chunk'),('pdf_pages','324')]:
            row={**self.row,key:value}
            self.assertEqual(self.enrich(row),row)

    def test_pure_idempotent_and_preserves_citation_metadata(self):
        before=copy.deepcopy(self.row);first=self.enrich(self.row)
        self.assertEqual(self.row,before)
        self.assertEqual(self.enrich(first),first)
        for key in before:
            if key!='content':self.assertEqual(first[key],before[key])

    def test_internal_markers_removed_preserving_math_citations(self):
        text='<think>hidden</think>MTBF = MTTF + MTTR。<!-- formula-not-decoded --> [片段2，教材第308页（PDF第323页）]'
        result=self.clean(text)
        self.assertNotIn('formula-not-decoded',result)
        self.assertNotIn('hidden',result)
        self.assertIn('公式未完整识别',result)
        self.assertIn('MTBF = MTTF + MTTR',result)
        self.assertIn('[片段2，教材第308页（PDF第323页）]',result)

    def test_unrecognized_formula_is_not_guessed(self):
        row={**self.row,'chunk_id':'unreviewed'}
        self.assertEqual(self.enrich(row),row)
        self.assertEqual(self.clean('公式：[公式占位]；C=2πr。'), '公式：[公式未完整识别]；C=2πr。')

if __name__=='__main__':unittest.main()
