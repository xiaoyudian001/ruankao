import asyncio,json,tempfile,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

class TokenUsageTests(unittest.TestCase):
 def module(self):
  import token_usage
  return token_usage
 def test_actual_response_and_missing_are_distinct(self):
  u=self.module();ledger=u.new_usage()
  u.add_response(ledger,SimpleNamespace(usage_metadata={'input_tokens':4800,'output_tokens':506,'total_tokens':5306},response_metadata={}), 'MiniMax-M3')
  self.assertEqual(ledger['inputTokens'],4800);self.assertEqual(ledger['outputTokens'],506)
  u.add_response(ledger,'plain text','MiniMax-M3')
  self.assertEqual(ledger['reportedCalls'],1);self.assertEqual(ledger['unreportedCalls'],1)
  self.assertIsNone(u.new_usage()['inputTokens'])
 def test_response_metadata_and_invalid_values(self):
  u=self.module();ledger=u.new_usage()
  u.add_response(ledger,SimpleNamespace(response_metadata={'token_usage':{'prompt_tokens':10,'completion_tokens':0,'total_tokens':10}}),'MiniMax-M3')
  self.assertEqual(ledger['outputTokens'],0)
  for v in (-1,True,'5',1.5):
   u.add_response(ledger,SimpleNamespace(usage_metadata={'input_tokens':v,'output_tokens':3,'total_tokens':5}),'MiniMax-M3')
  self.assertEqual(ledger['reportedCalls'],1);self.assertEqual(ledger['unreportedCalls'],4)
 def test_stream_uses_last_cumulative_report_once(self):
  import streaming
  u=self.module();ledger=u.new_usage();options=[]
  class Model:
   model_name='MiniMax-M3'
   async def astream(self,messages,**kwargs):
    options.append(kwargs)
    for text,n in [('<final_answer>正文',2),('</final_answer>',4)]:
     yield SimpleNamespace(content=text,usage_metadata={'input_tokens':8,'output_tokens':n,'total_tokens':8+n})
  async def run():
   with tempfile.TemporaryDirectory() as d:
    box=streaming.Mailbox('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',d)
    text=await streaming.consume_model(Model(),[],box,'qa',ledger)
    self.assertIn('正文',text)
  asyncio.run(run());self.assertEqual(ledger['inputTokens'],8);self.assertEqual(ledger['outputTokens'],4);self.assertEqual(ledger['reportedCalls'],1)
  self.assertTrue(options[0]['stream_options']['include_usage'])
 def test_generation_format_retry_counts_both_responses(self):
  from test_screenshot_generation import ScreenshotGenerationTests
  import base64
  class Model:
   model_name='MiniMax-M3';calls=0
   async def ainvoke(self,messages):
    self.calls+=1
    return SimpleNamespace(content='<final_answer>未闭合' if self.calls==1 else '<final_answer>答案</final_answer><used_figures>[]</used_figures>',usage_metadata={'input_tokens':10,'output_tokens':5,'total_tokens':15},response_metadata={})
  wire={'taskType':'qa','images':[],'references':[],'textPrompt':'正文','answerContext':'问题','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),text_model=Model(),vision_model=None)
  parsed=json.loads(asyncio.run(ScreenshotGenerationTests().builder()(stub)).text)
  self.assertEqual(parsed['tokenUsage']['inputTokens'],20);self.assertEqual(parsed['tokenUsage']['reportedCalls'],2)
 def test_visual_failure_marks_partial_usage_in_text_fallback(self):
  from single_pass import run_single_pass
  from test_single_pass import SinglePassTests
  local=SinglePassTests().local();ledger=self.module().new_usage();self.module().add_response(ledger,SimpleNamespace(usage_metadata={'input_tokens':10,'output_tokens':5,'total_tokens':15}),'MiniMax-M3')
  local.generate_evidence.side_effect=[TimeoutError(),{'answer':'正文回退','usedFigureIds':[],'tokenUsage':ledger}]
  with patch('single_pass.prepare_visual',return_value=([{'id':'a'*64}],{},[])):
   result=run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  self.assertEqual(result['tokenUsage']['inputTokens'],10);self.assertEqual(result['tokenUsage']['unreportedCalls'],1)
 def test_bridge_preserves_usage_outside_strict_answer_envelope(self):
  from bridge import LocalFlow
  from tempfile import TemporaryDirectory
  from unittest.mock import patch
  api=LocalFlow();usage={'scope':'answer_generation','inputTokens':10,'outputTokens':5,'totalTokens':15,'reportedCalls':1,'unreportedCalls':0,'models':['MiniMax-M3']}
  output={'outputs':[{'outputs':[{'outputs':{'visual_answer':{'message':json.dumps({'answer':'解析','usedFigureIds':[],'practice':None,'tokenUsage':usage})}}}]}]}
  with TemporaryDirectory() as d:
   Path(d,'single-pass-flows.json').write_text('{"generation":"test"}')
   with patch('bridge.ROOT',Path(d)),patch.object(api,'call',return_value=output):
    result=api.generate_evidence({'id':'x','task_type':'exam'},{'references':[],'textPrompt':'正文'},'问答题',[],{},20)
  self.assertEqual(result['tokenUsage'],usage)
 def test_failed_format_keeps_provider_usage_for_later_fallback(self):
  from test_screenshot_generation import ScreenshotGenerationTests
  import base64
  class Model:
   model_name='MiniMax-M3'
   async def ainvoke(self,messages):return SimpleNamespace(content='<final_answer>未闭合',usage_metadata={'input_tokens':10,'output_tokens':5,'total_tokens':15})
  wire={'taskType':'qa','images':[],'references':[],'textPrompt':'正文','answerContext':'问题','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),text_model=Model(),vision_model=None)
  parsed=json.loads(asyncio.run(ScreenshotGenerationTests().builder()(stub)).text)
  self.assertEqual(parsed['tokenUsage']['reportedCalls'],2);self.assertIn('generationError',parsed)
 def test_bridge_error_transports_known_usage(self):
  from bridge import LocalFlow
  usage=self.module().new_usage();self.module().add_response(usage,SimpleNamespace(usage_metadata={'input_tokens':10,'output_tokens':5,'total_tokens':15}),'MiniMax-M3')
  output={'outputs':[{'outputs':[{'outputs':{'visual_answer':{'message':json.dumps({'generationError':{'kind':'ValueError','reason':'Incomplete answer envelope'},'tokenUsage':usage})}}}]}]}
  with tempfile.TemporaryDirectory() as d:
   Path(d,'single-pass-flows.json').write_text('{"generation":"test"}')
   with patch('bridge.ROOT',Path(d)),patch.object(LocalFlow,'call',return_value=output):
    with self.assertRaises(ValueError) as caught:LocalFlow().generate_evidence({'id':'x'},{'references':[],'textPrompt':'正文'},'问题',[],{},20)
  self.assertEqual(caught.exception.token_usage,usage)
 def test_known_usage_from_failed_visual_is_merged(self):
  from single_pass import run_single_pass
  from test_single_pass import SinglePassTests
  ledger=self.module().new_usage();self.module().add_response(ledger,SimpleNamespace(usage_metadata={'input_tokens':10,'output_tokens':5,'total_tokens':15}),'MiniMax-M3')
  error=ValueError('Incomplete answer envelope');error.token_usage=ledger
  local=SinglePassTests().local();local.generate_evidence.side_effect=[error,{'answer':'正文回退','usedFigureIds':[],'tokenUsage':ledger.copy()}]
  with patch('single_pass.prepare_visual',return_value=([{'id':'a'*64}],{},[])):result=run_single_pass(local,{'question':'解释公式','id':'s','session_id':'s'})
  self.assertEqual(result['tokenUsage']['inputTokens'],20);self.assertEqual(result['tokenUsage']['unreportedCalls'],0)

if __name__=='__main__':unittest.main()
