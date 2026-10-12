import unittest,importlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
requires_catalog=unittest.skipUnless((Path(__file__).resolve().parent.parent/'output/sysarch-figure-rag/catalog.json').exists(),'需要本机自备教材图示目录；公开源码不包含教材索引')

class FigureTests(unittest.TestCase):
 def module(self):
  self.assertTrue((Path(__file__).parent/'figures.py').exists(),'figure retrieval not implemented')
  return importlib.import_module('figures')
 @requires_catalog
 def test_caption_match_and_unrelated_question(self):
  m=self.module();catalog=m.load_catalog()
  selected=m.select_figures('结合图12-2解释三层C/S与B/S结构',[],catalog)
  self.assertTrue(selected);self.assertIn('三层',selected[0]['caption']);self.assertEqual(selected[0]['pdfPage'],427)
  self.assertEqual(m.select_figures('系统架构设计师有哪些职责？',[],catalog),[])
  self.assertEqual(m.select_figures('解释MTBF是什么',[],catalog),[])
 @requires_catalog
 def test_decorations_filtered(self):
  m=self.module();catalog=m.load_catalog()
  self.assertTrue(catalog);self.assertTrue(all(18<=r['pdfPage']<=727 for r in catalog));self.assertTrue(all(r['bbox'][2]>.02 and r['bbox'][3]>.02 for r in catalog))
 @requires_catalog
 def test_full_text_reference_list_does_not_hide_explicit_figure(self):
  m=self.module();refs=[{'rank':i,'pdfPages':[427]} for i in range(1,11)]
  self.assertEqual(m.select_figures('解释图12-2的三层C/S与B/S结构',refs,m.load_catalog())[0]['pdfPage'],427)
 def test_failure_preserves_text_answer_and_reports_visual_failure(self):
  from unittest.mock import patch
  m=self.module();original={'answer':'正文答案','references':[],'retrievalQuery':'解释图12-2'}
  with patch.object(m,'enrich_answer',side_effect=TimeoutError):
   result=m.try_enrich_answer(None,{'question':'解释图12-2'},original,60)
  self.assertIn('正文答案',result['answer']);self.assertIn('原图解析',result['answer']);self.assertEqual(result['references'],[])
 def test_unknown_model_figure_refused(self):
  m=self.module()
  with self.assertRaises(ValueError):m.parse_visual_result('{"answer":"test","usedFigureIds":["unknown"]}',[])
 @requires_catalog
 def test_exact_number_skips_hybrid_and_hybrid_failure_keeps_caption_match(self):
  from unittest.mock import patch
  m=self.module();catalog=m.load_catalog()
  with patch('figure_hybrid.select_hybrid',side_effect=ValueError('stale index')) as hybrid:
   self.assertEqual(m.select_figures('解释图12-2',[],catalog)[0]['pdfPage'],427);hybrid.assert_not_called()
   self.assertTrue(m.select_figures('解释三层C/S与B/S结构',[],catalog));self.assertEqual(hybrid.call_count,1)
 @requires_catalog
 def test_image_is_checked_and_references_keep_source(self):
  m=self.module();selected=m.select_figures('解释图12-2的三层C/S与B/S结构',[],m.load_catalog())
  payload,refs=m.visual_payload('解释图12-2',[],selected)
  self.assertTrue(payload['images'][0]['dataUrl'].startswith('data:image/'))
  self.assertEqual(refs[0]['pdfPages'],[427]);self.assertIn('图',refs[0]['content']);self.assertNotIn('path',refs[0]['figures'][0])
  broken={**selected[0],'imageSha':'0'*64}
  with self.assertRaises(ValueError):m.visual_payload('图12-2',[],[broken])
if __name__=='__main__':unittest.main()
