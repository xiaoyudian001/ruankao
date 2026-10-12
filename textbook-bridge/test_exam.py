import unittest,json,importlib
from unittest.mock import Mock,patch

VALUE={'question':'可用性如何计算？','options':[{'label':label,'text':'选项'+label} for label in 'ABCD'],'correct':'A','explanation':'由本题公式得出。[片段1]','ranks':[1]}
class ExamTests(unittest.TestCase):
 def module(self):return importlib.import_module('exam')
 def test_generation_contract_keeps_practice_separate(self):
  m=self.module();raw='<final_answer>答案A。[片段1]</final_answer><used_figures>[]</used_figures><practice>'+json.dumps(VALUE,ensure_ascii=False)+'</practice>'
  result=m.parse_generation(m.serialize_generation(raw,[],[1],True),[],[1],True)
  self.assertEqual(result['practice']['correct'],'A');self.assertNotIn('可用性如何计算',result['answer'])
 def test_unknown_ranks_invalid_choice_and_incomplete_envelope_fail(self):
  m=self.module()
  for v in [{**VALUE,'correct':'Z'},{**VALUE,'ranks':[9]},{**VALUE,'explanation':'假的[片段9]'}]:
   with self.assertRaises(ValueError):m.validate_practice(v,[1])
  with self.assertRaises(ValueError):m.serialize_generation('<final_answer>答案</final_answer>',[],[1],True)
  self.assertIsNone(m.validate_practice(None,[]))
 def test_tagged_practice_preserves_unescaped_quotes_backslashes_and_newlines(self):
  m=self.module()
  explanation='名称 "System Architecture"，路径 C:\\notes\\new。\n依据[片段1]'
  raw='<final_answer>答案A[片段1]</final_answer><used_figures>[]</used_figures><practice><question>练习 "概念"</question>'+''.join('<option_'+label+'>内容'+label+'</option_'+label+'>' for label in 'ABCD')+'<correct>A</correct><explanation>'+explanation+'</explanation><ranks>[1]</ranks></practice>'
  result=m.parse_generation(m.serialize_generation(raw,[],[1],True),[],[1],True)
  self.assertEqual(result['practice']['explanation'],explanation)
 def test_practice_tag_order_does_not_change_meaning(self):
  m=self.module()
  fields={'correct':'A','ranks':'[1]','explanation':'说明[片段1]','question':'题目',**{'option_'+l:'内容'+l for l in 'ABCD'}}
  raw='<final_answer>答案A[片段1]</final_answer><used_figures>[]</used_figures><practice>'+''.join('<'+k+'>'+v+'</'+k+'>' for k,v in fields.items())+'</practice>'
  self.assertEqual(json.loads(m.serialize_generation(raw,[],[1],True))['practice']['correct'],'A')
 def test_invalid_optional_practice_preserves_original_analysis_without_another_call(self):
  m=self.module();invalid={**VALUE,'ranks':[99]}
  raw='<final_answer>原题解析[片段1]</final_answer><used_figures>[]</used_figures><practice>'+json.dumps(invalid,ensure_ascii=False)+'</practice>'
  result=json.loads(m.serialize_generation(raw,[],[1],True))
  self.assertEqual(result['answer'],'原题解析[片段1]');self.assertIsNone(result['practice'])
 def test_exam_routes_as_independent_question_and_generates_once(self):
  from single_pass import run_single_pass
  local=Mock();local.retrieve_evidence.return_value={'references':[],'rows':[],'textPrompt':'正文'}
  local.generate_evidence.return_value={'answer':'依据不足','usedFigureIds':[],'practice':None}
  job={'id':'exam','session_id':'s','question':'以下选项哪项属于架构师职责？ A.需求评估 B.其他','task_type':'exam','history_json':'not-json'}
  with patch('single_pass.prepare_visual',return_value=([],{},[])):
   result=run_single_pass(local,job)
  local.prepare_conversation.assert_not_called();local.generate_evidence.assert_called_once()
  self.assertIn('practice',result);self.assertEqual(result['timings']['answerCalls'],1)
 def test_distractor_server_does_not_trigger_visual_path(self):
  from single_pass import exam_needs_visual
  self.assertFalse(exam_needs_visual('系统架构设计师有哪些职责？\nA.评估需求\nB.只采购服务器'))
  self.assertTrue(exam_needs_visual('计算网络可用性，MTBF=199、MTTR=1。\nA.99.5%\nB.99%'))

if __name__=='__main__':unittest.main()
