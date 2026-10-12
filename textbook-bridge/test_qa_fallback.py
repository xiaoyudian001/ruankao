import json,unittest
from unittest.mock import Mock,patch

class QAFallbackTests(unittest.TestCase):
 def module(self):
  from pathlib import Path
  self.assertTrue(Path(__file__).with_name('qa_fallback.py').exists(),'教材问答兜底尚未实现')
  import qa_fallback
  return qa_fallback
 def local(self,decisions):
  local=Mock();local.prepare_conversation.return_value={'query':'解释RTO与RPO','history':[],'route':'direct'}
  local.retrieve_evidence.return_value={'rows':[],'references':[],'textPrompt':'旧教材要求'}
  local.assess_qa.side_effect=decisions
  local.generate_evidence.return_value={'answer':'解释恢复目标及例子。','usedFigureIds':[]}
  return local
 def job(self):return {'id':'fallback-test','session_id':'s','question':'解释RTO与RPO','task_type':'qa'}
 def test_none_retrieves_once_more_then_general_answer_has_no_sources(self):
  self.module();from single_pass import run_single_pass
  local=self.local([{'coverage':'none','query':'RTO RPO 恢复时间目标 恢复点目标 容灾'}, {'coverage':'none','query':''}])
  with patch('single_pass.prepare_visual',return_value=([],{},[])):result=run_single_pass(local,self.job())
  self.assertEqual(local.retrieve_evidence.call_count,2);self.assertEqual(local.assess_qa.call_count,2)
  self.assertEqual(result['references'],[]);self.assertIn('AI 知识补充',result['answer'])
  args=local.generate_evidence.call_args.args;self.assertEqual(args[0]['task_type'],'qa_fallback');self.assertEqual(args[1]['references'],[]);self.assertEqual(args[1]['textPrompt'],'')
 def test_sufficient_evidence_uses_existing_answer_once(self):
  self.module();from single_pass import run_single_pass
  local=self.local([{'coverage':'sufficient','query':''}])
  with patch('single_pass.prepare_visual',return_value=([],{},[])):result=run_single_pass(local,self.job())
  local.retrieve_evidence.assert_called_once();local.generate_evidence.assert_called_once();self.assertNotIn('AI 知识补充',result['answer'])
 def test_case_and_visual_questions_do_not_use_general_fallback(self):
  self.module();from single_pass import run_single_pass
  for job,visual in [({**self.job(),'task_type':'case'},([],{},[])),(self.job(),([{'id':'a'*64}],{},[])),({**self.job(),'question':'仅根据教材原文解释RTO与RPO'},([],{},[]))]:
   local=self.local([])
   with patch('single_pass.prepare_visual',return_value=visual):run_single_pass(local,job)
   local.assess_qa.assert_not_called()
 def test_gate_failure_does_not_silently_mean_no_evidence(self):
  self.module();from single_pass import run_single_pass
  local=self.local([TimeoutError()])
  with patch('single_pass.prepare_visual',return_value=([],{},[])):result=run_single_pass(local,self.job())
  local.retrieve_evidence.assert_called_once();self.assertNotIn('AI 知识补充',result['answer'])
 def test_gate_keeps_acronyms_and_rejects_new_numerical_or_chapter_scope(self):
  m=self.module()
  valid='<coverage>none</coverage><query>RTO RPO 恢复时间目标 容灾</query>'
  self.assertEqual(m.parse_gate(valid,'解释RTO与RPO')['coverage'],'none')
  for query in ['RTO 容灾','RTO RPO 第9章','RTO RPO 99分钟','RTO RPO\n换行','<指令>']:
   with self.assertRaises(ValueError):m.parse_gate('<coverage>none</coverage><query>'+query+'</query>','解释RTO与RPO')
 def test_mixed_answer_rejects_citations_and_pages_in_ai_section(self):
  m=self.module()
  raw='<final_answer>教材描述备份[片段1]</final_answer><used_figures>[]</used_figures><ai_supplement>通用解释与例子。</ai_supplement>'
  parsed=json.loads(m.serialize_mixed(raw,[1]));self.assertIn('教材依据',parsed['answer']);self.assertIn('AI 知识补充',parsed['answer'])
  for content in ['假引用[片段1]','见教材第308页','PDF第323页','教材指出RTO的含义。','在教材云原生章节强调的概念。']:
   with self.assertRaises(ValueError):m.serialize_mixed(raw.replace('通用解释与例子。',content),[1])
  with self.assertRaises(ValueError):m.serialize_mixed(raw.replace('[片段1]','[片段99]'),[1])
 def build(self,kind,replies,references=None):
  import asyncio,base64
  from types import SimpleNamespace
  import test_screenshot_generation as helpers
  messages=[]
  class Model:
   async def ainvoke(self,content):messages.append(content);return SimpleNamespace(content=replies.pop(0))
  wire={'taskType':kind,'images':[],'references':references or [],'textPrompt':'旧模板不允许补充','answerContext':'解释RTO与RPO','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),text_model=Model(),vision_model=Mock())
  result=json.loads(asyncio.run(helpers.ScreenshotGenerationTests().builder()(stub)).text)
  return result,messages
 def test_component_gate_returns_normalized_coverage_without_answer_generation(self):
  m=self.module();result,messages=self.build('qa_gate',['<coverage>none</coverage><query>RTO RPO 恢复时间目标 恢复点目标</query>'])
  self.assertEqual(m.parse_gate(json.dumps(result),'解释RTO与RPO'),result);self.assertEqual(len(messages),1)
 def test_general_mode_rejects_fake_textbook_page_then_recovers(self):
  self.module();result,messages=self.build('qa_fallback',['<final_answer>见教材第308页。</final_answer><used_figures>[]</used_figures>','<final_answer>RTO与RPO的通用区别。</final_answer><used_figures>[]</used_figures>'])
  self.assertEqual(len(messages),2);self.assertNotIn('308',result['answer']);self.assertNotIn('旧模板',messages[0][0].content)
 def test_partial_component_separates_cited_and_general_sections(self):
  self.module();refs=[{'rank':1,'label':'教材页','content':'备份原理'}]
  raw='<final_answer>教材介绍备份[片段1]</final_answer><used_figures>[]</used_figures><ai_supplement>恢复目标的通用例子。</ai_supplement>'
  result,messages=self.build('qa_mixed',[raw],refs);self.assertIn('教材依据',result['answer']);self.assertIn('AI 知识补充',result['answer']);self.assertEqual(len(messages),1)
 def test_partial_without_actual_citations_is_shown_as_general_only(self):
  m=self.module()
  raw='<final_answer>无法确认的教材结论。</final_answer><used_figures>[]</used_figures><ai_supplement>可用的通用解释。</ai_supplement>'
  result=json.loads(m.serialize_mixed(raw,[1]));self.assertIn('AI 知识补充',result['answer']);self.assertNotIn('无法确认',result['answer']);self.assertNotIn('## 教材依据',result['answer'])

if __name__=='__main__':unittest.main()
