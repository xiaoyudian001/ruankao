import unittest
from unittest.mock import Mock,patch
from pathlib import Path
import importlib

class SinglePassTests(unittest.TestCase):
 def module(self):
  self.assertTrue(Path(__file__).with_name('single_pass.py').exists(),'single-pass routing missing')
  return importlib.import_module('single_pass')
 def local(self):
  local=Mock()
  local.prepare_conversation.return_value={'query':'解释公式','route':'direct','history':[]}
  local.retrieve_evidence.return_value={'references':[],'rows':[],'textPrompt':'教材规则与正文'}
  local.generate_evidence.return_value={'answer':'依据原文的答案','usedFigureIds':[]}
  return local
 def test_visual_path_generates_once_and_never_runs_old_answer(self):
  m=self.module();local=self.local();image={'id':'a'*64}
  with patch.object(m,'prepare_visual',return_value=([image],{},[])):
   result=m.run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  local.generate_evidence.assert_called_once();local.run_conversation.assert_not_called()
  self.assertEqual(result['timings']['answerCalls'],1)
 def test_plain_text_path_generates_once(self):
  m=self.module();local=self.local()
  with patch.object(m,'prepare_visual',return_value=([],{},[])):
   result=m.run_single_pass(local,{'question':'架构师职责','id':'s','session_id':'s'})
  self.assertEqual(result['answer'],'依据原文的答案');local.generate_evidence.assert_called_once()
  self.assertEqual(result['timings']['answerCalls'],1)
 def test_image_failure_uses_same_evidence_for_one_text_answer(self):
  m=self.module();local=self.local()
  with patch.object(m,'prepare_visual',side_effect=OSError('image unreadable')):
   result=m.run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  local.retrieve_evidence.assert_called_once();local.generate_evidence.assert_called_once()
  self.assertIn('未完成',result['answer']);self.assertEqual(result['timings']['answerCalls'],1)
 def test_failed_visual_generation_retries_text_without_retrieving_again(self):
  m=self.module();local=self.local();image={'id':'a'*64}
  local.generate_evidence.side_effect=[TimeoutError(),{'answer':'正文回退','usedFigureIds':[]}]
  with patch.object(m,'prepare_visual',return_value=([image],{},[])):
   result=m.run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  local.retrieve_evidence.assert_called_once();self.assertEqual(local.generate_evidence.call_count,2)
  self.assertIn('正文回退',result['answer']);self.assertEqual(result['timings']['answerCalls'],2)
 def test_ambiguous_followup_does_not_retrieve_or_generate(self):
  m=self.module();local=self.local();local.prepare_conversation.return_value={'query':'','route':'clarification','history':[]}
  result=m.run_single_pass(local,{'question':'它呢','id':'s','session_id':'s'})
  local.retrieve_evidence.assert_not_called();local.generate_evidence.assert_not_called()
  self.assertEqual(result['timings']['answerCalls'],0)
 def test_unused_images_keep_generated_answer_and_only_text_sources(self):
  m=self.module();local=self.local()
  with patch.object(m,'prepare_visual',return_value=([{'id':'a'*64}],{},[{'rank':9,'figures':[{'id':'a'*64}]}])):
   result=m.run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  self.assertEqual(result['references'],[]);self.assertEqual(result['answer'],'依据原文的答案')
 def test_generation_transport_preserves_history_quotes_and_math_slashes(self):
  import base64,json
  from bridge import LocalFlow
  from test_conversation_bridge import langflow_string
  local=LocalFlow();context='历史包含 "引号"\nC:\\notes\\new；数学 \\nu。'
  def call(path,body=None,**kwargs):
   encoded=langflow_string(body['input_request']['input_value'])
   data=json.loads(base64.b64decode(encoded.split(':',1)[1],validate=True))
   self.assertEqual(data['answerContext'],context)
   self.assertEqual(data['images'],[])
   return {'outputs':[{'outputs':[{'outputs':{'visual_answer':{'message':'{"answer":"教材回答","usedFigureIds":[]}'}}}]}]}
  from tempfile import TemporaryDirectory
  with TemporaryDirectory() as temporary:
   (Path(temporary)/'single-pass-flows.json').write_text(json.dumps({'generation':'test-generation'}),encoding='utf-8')
   with patch('bridge.ROOT',Path(temporary)),patch.object(local,'call',side_effect=call):
    answer=local.generate_evidence({'id':'history-check'},{'textPrompt':'教材提示','references':[]},context,[],{},timeout=20)
  self.assertEqual(answer['answer'],'教材回答')
 def test_invalid_visual_citation_falls_back_to_same_text_snapshot(self):
  m=self.module();local=self.local()
  local.generate_evidence.side_effect=[{'answer':'错误引用[片段99]','usedFigureIds':[]},{'answer':'正文回退','usedFigureIds':[]}]
  with patch.object(m,'prepare_visual',return_value=([{'id':'a'*64}],{},[])):
   result=m.run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  self.assertIn('正文回退',result['answer']);local.retrieve_evidence.assert_called_once()
  self.assertEqual(result['timings']['answerCalls'],2)
 def test_single_calculation_uses_one_original_and_matching_chapter_evidence(self):
  m=self.module()
  originals=[{'id':'a'*64,'kind':'formula','chapter':'第17章网络'},{'id':'b'*64,'kind':'formula','chapter':'第9章可靠性'}]
  refs=[{'rank':1,'chapter':'第17章网络'},{'rank':2,'chapter':'第9章可靠性'}]
  chosen,kept=m.focus_calculation('MTBF=199小时、MTTR=1小时，计算可用性',originals,refs)
  self.assertEqual(chosen,[originals[0]]);self.assertEqual(kept,[refs[0]])
  self.assertEqual(m.focus_calculation('比较两章的公式区别并计算',originals,refs),(originals,refs))

if __name__=='__main__':unittest.main()
