import unittest,json
from unittest.mock import Mock
class EssayTests(unittest.TestCase):
 def task(self,kind='feedback'):
  return {'kind':kind,'topic':'论架构设计','requirements':'结合项目','projectFacts':'真实事实 "负责架构"\n没有性能指标','version':2,'section':'架构方案' if kind=='feedback' else '', 'draft':'本段草稿' if kind=='feedback' else ''}
 def test_model_receives_facts_but_retrieval_uses_topic_not_project_details(self):
  from essays import run_essay
  local=Mock();local.retrieve_evidence.return_value={'references':[],'textPrompt':'教材','rows':[]};local.generate_evidence.return_value={'answer':'请补充指标','usedFigureIds':[]}
  task=self.task();result=run_essay(local,{'id':'essay-test','task_type':'essay','task_payload_json':json.dumps(task)},budget=100)
  plan=local.retrieve_evidence.call_args.args[1];self.assertIn('论架构设计',plan['query']);self.assertNotIn('真实事实',plan['query'])
  self.assertEqual(local.generate_evidence.call_args.args[4]['essayTask']['projectFacts'],task['projectFacts']);self.assertEqual(result['answer'],'请补充指标');self.assertEqual(result['rewriteRoute'],'direct')
 def test_bounds_and_instruction_do_not_allow_fabricated_project_results(self):
  from essays import validate_essay_task,essay_system
  with self.assertRaises(ValueError):validate_essay_task({**self.task(),'projectFacts':''})
  with self.assertRaises(ValueError):validate_essay_task({**self.task(),'kind':'execute'})
  self.assertIn('不得编造',essay_system('outline'));self.assertIn('逐段',essay_system('feedback'))
 def test_essay_facts_reach_text_model_with_no_practice_or_image_output(self):
  import asyncio,base64
  from types import SimpleNamespace
  from test_screenshot_generation import ScreenshotGenerationTests
  captured=[]
  class Model:
   async def ainvoke(self,messages):
    captured.extend(messages);return SimpleNamespace(content='<final_answer>提纲：先补充真实效果[片段1]</final_answer>')
  task=self.task('outline');wire={'taskType':'essay','essayTask':task,'images':[],'references':[{'rank':1,'label':'教材页','content':'技术权衡需要结合质量属性'}],'textPrompt':'正文','answerContext':'论文训练','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),text_model=Model(),vision_model=Mock())
  answer=json.loads(asyncio.run(ScreenshotGenerationTests().builder()(stub)).text)
  self.assertNotIn('practice',answer);self.assertEqual(answer['usedFigureIds'],[]);self.assertIn('真实事实',captured[1].content);self.assertIn('不得编造',captured[0].content);stub.vision_model.ainvoke.assert_not_called()
