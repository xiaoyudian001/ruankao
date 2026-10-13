import ast,asyncio,base64,json,re,struct,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from single_pass_components import generation_code

class ScreenshotGenerationTests(unittest.TestCase):
 def builder(self):
  tree=ast.parse(generation_code());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)];build=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.AsyncFunctionDef));functions.append(build)
  from exam import EXAM_SYSTEM
  ns={'EXAM_SYSTEM':EXAM_SYSTEM,'asyncio':asyncio,'base64':base64,'json':json,'re':re,'struct':struct,'Message':lambda **kw:SimpleNamespace(**kw),'SystemMessage':lambda **kw:SimpleNamespace(**kw),'HumanMessage':lambda **kw:SimpleNamespace(**kw)}
  import streaming
  ns.update({name:getattr(streaming,name) for name in ('Mailbox','consume_model','visible_answer','GenerationStopped','os','shutil','tempfile','time','uuid','Path')})
  exec(compile(ast.Module(body=functions,type_ignores=[]),'generation','exec'),ns);return ns['build']
 def image(self):
  raw=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',600,800)+b'\x00'*16
  return {'dataUrl':'data:image/png;base64,'+base64.b64encode(raw).decode(),'width':600,'height':800}
 def test_edited_question_and_screenshot_reach_vision_model_not_text_model(self):
  captured=[]
  class Model:
   async def ainvoke(self,messages):captured.extend(messages);return SimpleNamespace(content='<final_answer>答案A[片段1]</final_answer><used_figures>[]</used_figures><practice>null</practice>')
  wire={'taskType':'exam','questionImages':[self.image()],'images':[],'references':[{'rank':1,'label':'教材15页','content':'需求评估'}],'textPrompt':'正文','answerContext':'已核对后的题干','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),vision_model=Model(),text_model=Mock())
  result=asyncio.run(self.builder()(stub));self.assertIn('答案A',result.text);stub.text_model.ainvoke.assert_not_called();self.assertIn('已核对后的题干',captured[1].content[0]['text']);self.assertTrue(any(c['type']=='image_url' for c in captured[1].content));self.assertIn('不是教材出处',captured[0].content)
 def test_screenshot_failure_does_not_retry_without_user_image(self):
  from single_pass import run_single_pass
  local=Mock();local.retrieve_evidence.return_value={'references':[],'rows':[],'textPrompt':'正文'};local.generate_evidence.side_effect=TimeoutError()
  with patch('single_pass.prepare_visual',return_value=([{'id':'a'*64}],{},[])):
   with self.assertRaises(TimeoutError):run_single_pass(local,{'id':'s','session_id':'s','task_type':'exam','question':'请解释原图公式','question_images':[self.image()]})
  local.generate_evidence.assert_called_once()
 def test_open_question_recovers_once_without_forcing_practice(self):
  captured=[]
  class Model:
   async def ainvoke(self,messages):
    captured.append(messages)
    return SimpleNamespace(content='<final_answer>未闭合' if len(captured)==1 else '<final_answer>逐问解析[片段1]</final_answer>')
  model=Model();wire={'taskType':'case','images':[],'references':[{'rank':1,'label':'教材页','content':'架构可复用结构'}],'textPrompt':'正文','answerContext':'共享背景。请回答：1.是否架构复用？','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),vision_model=Mock(),text_model=model)
  result=json.loads(asyncio.run(self.builder()(stub)).text)
  self.assertEqual(len(captured),2);self.assertIsNone(result['practice']);self.assertIn('逐个小问',captured[0][0].content)
 def test_image_name_is_rejected_then_recovered_with_explicit_allowlist(self):
  calls=[]
  class Model:
   async def ainvoke(self,messages):
    calls.append(messages)
    figure='用户截图1' if len(calls)==1 else 'a'*64
    return SimpleNamespace(content='<final_answer>解析[片段1]</final_answer><used_figures>'+json.dumps([figure])+'</used_figures>')
  wire={'taskType':'exam','images':[{'id':'a'*64,'rank':1,'caption':'原页','dataUrl':self.image()['dataUrl']}],'references':[{'rank':1,'label':'教材页','content':'教材内容','figures':[{'id':'a'*64}]}],'textPrompt':'正文','answerContext':'请解释此案例','timeoutSeconds':10}
  stub=SimpleNamespace(payload='single-answer-b64-v1:'+base64.b64encode(json.dumps(wire).encode()).decode(),vision_model=Model(),text_model=Mock())
  result=json.loads(asyncio.run(self.builder()(stub)).text)
  self.assertEqual(len(calls),2);self.assertEqual(result['usedFigureIds'],['a'*64]);self.assertIn('不要填写图号',calls[0][0].content)
if __name__=='__main__':unittest.main()
