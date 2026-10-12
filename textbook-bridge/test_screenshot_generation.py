import ast,asyncio,base64,json,re,struct,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from single_pass_components import generation_code

class ScreenshotGenerationTests(unittest.TestCase):
 def builder(self):
  tree=ast.parse(generation_code());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)];build=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.AsyncFunctionDef));functions.append(build)
  ns={'asyncio':asyncio,'base64':base64,'json':json,'re':re,'struct':struct,'Message':lambda **kw:SimpleNamespace(**kw),'SystemMessage':lambda **kw:SimpleNamespace(**kw),'HumanMessage':lambda **kw:SimpleNamespace(**kw)}
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
if __name__=='__main__':unittest.main()
