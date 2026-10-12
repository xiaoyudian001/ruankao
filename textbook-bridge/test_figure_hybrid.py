import unittest,importlib
from pathlib import Path
import numpy as np

class FigureHybridTests(unittest.TestCase):
 def module(self):
  self.assertTrue((Path(__file__).parent/'figure_hybrid.py').exists(),'hybrid figure index missing')
  return importlib.import_module('figure_hybrid')
 def rows(self):
  return [{'id':str(i)*64,'caption':c,'context':t,'chapter':'第12章','pdfPage':400+i} for i,c,t in [(1,'图12-2 三层C/S与B/S架构','表示层、功能层、数据层'),(2,'图12-4 MVC架构','模型、视图、控制器'),(3,'图12-5 数据管道','过滤器和转换')]]
 def test_semantic_candidate_without_keyword_overlap(self):
  m=self.module();index=m.FigureIndex(self.rows(),np.eye(3))
  pool=index.candidates('打开网页后后台如何响应',[1,0,0])
  self.assertEqual(pool[0]['chunk_id'],'1'*64);self.assertEqual(pool[0]['dense_rank'],1)
 def test_rrf_merges_same_source_once(self):
  m=self.module();index=m.FigureIndex(self.rows(),np.eye(3))
  pool=index.candidates('三层C/S架构',[1,0,0]);self.assertEqual(len({r['chunk_id'] for r in pool}),len(pool));self.assertIsNotNone(pool[0]['lexical_rank'])
 def test_invalid_vectors_and_query_dimensions_rejected(self):
  m=self.module()
  for vectors in [np.zeros((3,3)),np.full((3,3),np.nan),np.full((3,3),1e30),np.eye(2)]:
   with self.assertRaises(ValueError):m.FigureIndex(self.rows(),vectors)
  index=m.FigureIndex(self.rows(),np.eye(3))
  for query in [[0,0,0],[1,2],[float('nan'),0,1]]:
   with self.assertRaises(ValueError):index.candidates('检索',query)
 def test_fingerprint_tracks_context_and_caption(self):
  m=self.module();rows=self.rows();original=m.document_fingerprint(rows)
  changed=[{**r,'context':r['context']+' new'} for r in rows]
  self.assertNotEqual(original,m.document_fingerprint(changed))
 def test_exact_figure_number_and_plain_role_skip_embedding(self):
  m=self.module();self.assertFalse(m.needs_hybrid('系统架构设计师有哪些职责？'))
  self.assertTrue(m.needs_hybrid('浏览器访问网站时，三层分别做什么？'))
  self.assertTrue(m.needs_hybrid('打开网页后，客户端和后台怎么交互？'))
  self.assertTrue(m.needs_hybrid('事件从产生到处理要经过哪些环节？'))
 def test_stale_document_or_vector_digest_is_rejected(self):
  import io,json,hashlib
  m=self.module();rows=self.rows();catalog=json.dumps({'bookSha':m.BOOK_SHA,'figures':rows}).encode()
  binary=io.BytesIO();np.savez_compressed(binary,vectors=np.eye(3));raw=binary.getvalue()
  manifest={'bookSha':m.BOOK_SHA,'model':m.MODEL,'documentsSha':m.document_fingerprint(rows),'catalogSha':hashlib.sha256(catalog).hexdigest(),'count':3,'dimensions':3,'vectorsSha':hashlib.sha256(raw).hexdigest()}
  m._load(catalog,json.dumps(manifest).encode(),raw)
  for key in ['documentsSha','catalogSha','vectorsSha']:
   with self.assertRaises(ValueError):m._load(catalog,json.dumps({**manifest,key:'bad'}).encode(),raw)
 def test_strong_semantic_top_match_survives_mild_negative_local_logit(self):
  m=self.module();row={'dense_rank':1,'dense_score':.66,'lexical_rank':8,'caption_matches':0}
  self.assertTrue(m.relevant_candidate(row,-2.3))
  self.assertFalse(m.relevant_candidate({**row,'dense_rank':18,'dense_score':.57},-2.0))
  self.assertFalse(m.relevant_candidate(row,-6.0))
  self.assertFalse(m.relevant_candidate({'dense_rank':None,'dense_score':.56,'lexical_rank':1,'caption_matches':0},-.13))
if __name__=='__main__':unittest.main()
