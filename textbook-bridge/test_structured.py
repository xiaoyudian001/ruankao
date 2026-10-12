import importlib, unittest
from pathlib import Path
from unittest.mock import patch

class StructuredTests(unittest.TestCase):
 def module(self):
  self.assertTrue((Path(__file__).parent/'structured.py').exists(),'structured evidence not implemented')
  return importlib.import_module('structured')
 def test_tables_keep_rows_and_column_identity(self):
  m=self.module();text='表2-2 存取控制矩阵\n\n|用户|ALPHA|REPORT|\n|---|---|---|\n|张军|RWX|R-X|\n|王伟||R-X|\n'
  blocks=m.table_blocks(text);self.assertEqual(len(blocks),1)
  self.assertIn('|张军|RWX|R-X|',blocks[0]);self.assertIn('|王伟||R-X|',blocks[0])
  self.assertEqual(m.table_blocks('普通正文 | 分隔符\n'),[])
 def test_formula_missing_stays_missing_and_actual_line_is_preserved(self):
  m=self.module();self.assertEqual(m.formula_lines('<!-- formula-not-decoded -->'),[])
  self.assertEqual(m.formula_lines('可用性如下：\n\nA=MTBF/(MTBF+MTTR)\n\n正文'),['A=MTBF/(MTBF+MTTR)'])
  self.assertEqual(m.formula_lines('系统特点=可靠性和安全性'),[])
 def test_question_routing(self):
  m=self.module();self.assertIn('formula',m.question_kinds('解释MTBF、MTTR与可用性的关系并举一个计算例子'))
  self.assertIn('table',m.question_kinds('结合表2-2说明张军能访问哪些文件'))
  self.assertEqual(m.question_kinds('系统架构设计师有哪些职责？'),set())
  self.assertEqual(m.question_kinds('解释MTBF是什么'),set())
 def test_continuation_requires_adjacent_matching_columns(self):
  m=self.module();text='(续表)\n\n|用户|ALPHA|REPORT|\n|---|---|---|\n|李晓钢|R-X|RWX|\n'
  previous={'page':55,'title':'表2-2 存取控制矩阵','header':'|用户|ALPHA|REPORT|'}
  self.assertIn('表2-2',m.continuation_title(text,m.table_blocks(text),previous,56))
  self.assertEqual(m.continuation_title(text,m.table_blocks(text),previous,57),'')
  self.assertEqual(m.continuation_title(text.replace('REPORT','BETA'),m.table_blocks(text.replace('REPORT','BETA')),previous,56),'')
 def test_exact_table_and_no_cross_kind(self):
  m=self.module();rows=[{'id':'a'*64,'kind':'table','kinds':['table'],'caption':'表 2-2 存取控制矩阵','pdfPage':55,'context':'张军 ALPHA RWX'}, {'id':'b'*64,'kind':'formula','kinds':['formula'],'caption':'公式原页','pdfPage':628,'context':'A=MTBF/(MTBF+MTTR)'}]
  self.assertEqual(m.select_structured('说明表2-2',[],rows),rows[:1])
  self.assertEqual(m.select_structured('系统架构设计师有哪些职责？',[],rows),[])
 def test_formula_topic_terms_and_direct_query_are_not_duplicated(self):
  m=self.module();from figures import visual_query
  q='解释MTBF、MTTR与可用性公式'
  self.assertEqual(visual_query(q,q),q)
  rows=[{'context':'架构可靠性距离计算方法'},{'context':'A=MTBF/(MTBF+MTTR)'}]
  self.assertEqual(m.topic_rows(q,rows),rows[1:])
 def test_index_failure_uses_actual_retrieved_page_only(self):
  m=self.module();rows=[{'id':'a'*64,'kind':'formula','kinds':['formula'],'caption':'网络可用性原页','chapter':'第17章','pdfPage':628,'context':'可用性 A=MTBF/(MTBF+MTTR)'}, {'id':'b'*64,'kind':'formula','kinds':['formula'],'caption':'网络可用性原页','chapter':'第17章','pdfPage':629,'context':'可用性 A=MTBF/(MTBF+MTTR)'}]
  with patch.object(m,'load_index',side_effect=ValueError('stale')):
   self.assertEqual(m.select_structured('可用性MTBF和MTTR公式',[{'pdfPages':[628]}],rows),rows[:1])
 def test_snapshot_and_trusted_rendering(self):
  m=self.module();r={'id':'a'*64,'kind':'formula','kinds':['formula'],'caption':'公式原页','pdfPage':628,'bbox':[0,0,1,1],'pageSize':[500,700]}
  with patch.object(m,'PageRenderer') as renderer:
   with self.assertRaises(ValueError):m.materialize([{**r,'pdfPage':0}])
   with self.assertRaises(ValueError):m.materialize([{**r,'id':'../../outside'}])
   renderer.assert_not_called()
 def test_new_types_survive_payload_and_are_verified(self):
  m=self.module();from figures import visual_payload
  import hashlib,tempfile
  m.IMAGES.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=m.IMAGES) as tmp:
   p=Path(tmp)/'verified.png';p.write_bytes(b'original-png')
   r={'id':'a'*64,'kind':'formula','caption':'公式原页','pdfPage':628,'bbox':[0,0,1,1],'pageSize':[500,700],'path':str(p),'imageSha':hashlib.sha256(p.read_bytes()).hexdigest(),'context':'原页公式','label':'教材第613页（PDF第628页）','chapter':'第17章'}
   payload,refs=visual_payload('可用性公式',[],[r]);self.assertEqual(refs[0]['figures'][0]['kind'],'formula')
   self.assertNotIn('path',refs[0]['figures'][0]);self.assertEqual(len(payload['images']),1)
   with self.assertRaises(ValueError):visual_payload('公式',[],[{**r,'imageSha':'0'*64}])
   with self.assertRaises(ValueError):visual_payload('公式',[],[r,r,r])
 def test_visual_wire_handles_quotes_backslashes_and_newlines(self):
  from figures import serialize_visual_result,parse_visual_result
  ident='a'*64;answer='表格中 "R-X" 表示读和执行。\n例子路径 C:\\教材\\公式。'
  wire='<final_answer>'+answer+'</final_answer>\n<used_figures>["'+ident+'"]</used_figures>'
  parsed=parse_visual_result(serialize_visual_result(wire,[ident]),[ident]);self.assertEqual(parsed['answer'],answer)
  with self.assertRaises(ValueError):serialize_visual_result(wire,["b"*64])
 def test_original_page_citation_footer_uses_actual_ranks_only(self):
  from figures import cite_original_pages
  refs=[{'rank':9,'label':'教材第613页（PDF第628页）','figures':[{'id':'a'*64}]}]
  self.assertIn('[片段9]',cite_original_pages('公式解释',refs))
  self.assertEqual(cite_original_pages('见[片段9]',refs),'见[片段9]')

if __name__=='__main__':unittest.main()
