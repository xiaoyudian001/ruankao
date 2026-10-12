"""Ordinary QA uses the same bounded output recovery as exam/essay generation."""
import asyncio,base64,json,unittest
from types import SimpleNamespace
from unittest.mock import Mock
import test_screenshot_generation as screenshot_module

class AnswerGenerationTests(unittest.TestCase):
 def run_replies(self,replies,seconds=10):
  calls=[];self.calls=calls
  class Model:
   async def ainvoke(self,messages):calls.append(messages);return SimpleNamespace(content=replies.pop(0))
  wire={'taskType':'qa','images':[],'references':[{'rank':1,'label':'教材页','content':'原文片段'}],'textPrompt':'按教材回答','answerContext':'解释一下 RTO 与 RPO','timeoutSeconds':seconds}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),text_model=Model(),vision_model=Mock())
  result=asyncio.run(screenshot_module.ScreenshotGenerationTests().builder()(stub))
  stub.vision_model.ainvoke.assert_not_called()
  return json.loads(result.text),calls
 def test_plain_qa_recovers_malformed_reply_with_same_question(self):
  result,calls=self.run_replies(['当前资料未说明这两个术语。','<final_answer>当前检索片段不足以解释这两个术语。</final_answer><used_figures>[]</used_figures>'])
  self.assertEqual(len(calls),2);self.assertIn('不足',result['answer']);self.assertNotIn('practice',result)
  self.assertEqual(calls[0][1].content,calls[1][1].content);self.assertIn('RTO',calls[1][1].content)
 def test_closed_text_answer_missing_figure_declaration_is_safe(self):
  from figures import serialize_visual_result
  raw='<final_answer>说明 "RTO"\n正文 C:\\notes\\new。</final_answer>'
  result=json.loads(serialize_visual_result(raw,[]));self.assertEqual(result['usedFigureIds'],[]);self.assertIn('C:\\notes\\new',result['answer'])
 def test_truncated_answer_and_partial_figure_declaration_stay_invalid(self):
  from figures import serialize_visual_result
  for raw in ['<final_answer>未完成','<final_answer>答案</final_answer><used_figures>[','<final_answer>答案</final_answer>额外文字']:
   with self.assertRaises(ValueError):serialize_visual_result(raw,[])
 def test_qa_unknown_citations_are_rewritten_then_still_rejected(self):
  bad='<final_answer>伪造来源[片段99]</final_answer><used_figures>[]</used_figures>'
  with self.assertRaisesRegex(ValueError,'Unknown answer citation'):self.run_replies([bad,bad])
  self.assertEqual(len(self.calls),2)
 def test_short_remaining_budget_does_not_start_rewrite(self):
  with self.assertRaisesRegex(ValueError,'Invalid answer JSON'):self.run_replies(['不合规的裸正文'],seconds=1)
  self.assertEqual(len(self.calls),1)
 def test_fenced_tagged_reply_is_accepted_without_losing_answer(self):
  from figures import serialize_visual_result
  result=json.loads(serialize_visual_result('```xml\n<final_answer>正文[片段1]</final_answer><used_figures>[]</used_figures>\n```',[]))
  self.assertEqual(result['answer'],'正文[片段1]')
 def test_json_failure_has_safe_answer_category(self):
  import io
  from urllib.error import HTTPError
  from flow_errors import failure_message
  error=HTTPError('http://localhost',500,'error',{},io.BytesIO(b'{"error":"Invalid answer JSON","secret":"private"}'))
  text=failure_message(error);self.assertIn('答案格式',text);self.assertNotIn('private',text)

if __name__=='__main__':unittest.main()
