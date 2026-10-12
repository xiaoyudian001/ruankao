"""Langflow retrieval snapshot and one selected-model generation component."""
import inspect
from pathlib import Path
from figures import SYSTEM,parse_visual_result,serialize_visual_result
from exam import EXAM_SYSTEM,question_kind,exam_system,reconcile_sources,validate_practice,parse_generation,serialize_generation
from screenshots import RECOGNITION_SYSTEM,parse_recognition,validate_question_images
from essays import validate_essay_task,essay_system

HERE=Path(__file__).resolve().parent.parent/'sysarch-fullbook'
PURE='\n'.join((HERE/n).read_text(encoding='utf-8') for n in ['citation_format.py','source_references.py']).replace('from citation_format import source_hint\n','')
SNAPSHOT_CODE=PURE+'''
from lfx.custom import Component
from lfx.io import HandleInput,MessageInput,Output
from lfx.schema.data import Data
class TextbookEvidenceSnapshot(Component):
 display_name="检索证据快照 · 不生成答案"
 name="TextbookEvidenceSnapshot"
 inputs=[HandleInput(name="rows",display_name="本次有序教材片段",input_types=["DataFrame","Table"],required=True),MessageInput(name="text_prompt",display_name="原教学提示模板",required=True)]
 outputs=[Output(name="evidence",display_name="正文与来源快照",method="build")]
 def build(self)->Data:
  raw=self.rows.to_dict(orient='records')
  keys=('source_sha256','chunk_id','pdf_page_start','pdf_page_end','book_page_start','book_page_end','book_pages','book_page_mapping_status','chapter','source_file','content')
  rows=[{k:r[k] for k in keys if k in r} for r in raw]
  refs=source_references(rows)
  if len(rows)>10 or len(refs)!=len(rows):raise ValueError('Invalid snapshot source identity or order')
  return Data(data={'rows':rows,'references':refs,'textPrompt':self.text_prompt.get_text()})
'''

def generation_code():
 return '''
import asyncio,base64,json,re,struct,time
from langchain_core.messages import SystemMessage,HumanMessage
from lfx.custom import Component
from lfx.io import MessageTextInput,HandleInput,Output
from lfx.schema.message import Message
'''+ 'EXAM_SYSTEM='+repr(EXAM_SYSTEM)+'\n'+inspect.getsource(validate_essay_task)+'\n'+inspect.getsource(essay_system)+'\n'+inspect.getsource(question_kind)+'\n'+inspect.getsource(exam_system)+'\n'+inspect.getsource(reconcile_sources)+'\n'+inspect.getsource(parse_visual_result)+'\n'+inspect.getsource(serialize_visual_result)+'\n'+inspect.getsource(validate_practice)+'\n'+inspect.getsource(parse_generation)+'\n'+inspect.getsource(serialize_generation)+'\n'+inspect.getsource(parse_recognition)+'\n'+inspect.getsource(validate_question_images)+'''
class TextbookSingleEvidenceAnswer(Component):
 display_name="教材一次作答 · 正文或原页"
 description="证据准备完成后，按是否有原页调用一个MiniMax模型句柄。"
 name="TextbookSingleEvidenceAnswer"
 inputs=[MessageTextInput(name="payload",display_name="本轮证据与问题",required=True),HandleInput(name="text_model",display_name="MiniMax正文模型",input_types=["LanguageModel"],required=True),HandleInput(name="vision_model",display_name="MiniMax原页模型",input_types=["LanguageModel"],required=True)]
 outputs=[Output(name="visual_answer",display_name="最终答案与实际采用来源",method="build")]
 async def build(self)->Message:
  if not self.payload.startswith('single-answer-b64-v1:') or len(self.payload)>20*1024*1024:raise ValueError('Invalid evidence transport')
  data=json.loads(base64.b64decode(self.payload.split(':',1)[1],validate=True))
  if len(data['images'])>2 or len(data['references'])>10:raise ValueError('Evidence budget exceeded')
  question_images=validate_question_images(data.get('questionImages',[]))
  if question_images and data.get('taskType') not in ('exam','recognize'):raise ValueError('Screenshots require an exam task')
  if data['images']:
   system='''+repr(SYSTEM+'\n精简作答：只转录本题直接需要的表格或公式，不展开未请求的其他指标、积分或旁支公式。通常只写“直接答案/必要解释”“计算示例（需要时）”“引用”。用户未要求逐图说明时，不另写读图报告；完整原页不要称为教材编号图1或图2。同名变量在不同章节的定义不同，不能称为一致或相互印证；不参与本题计算的章节公式直接省略。保持必要条件与引用，避免重复总结，优先用500～1000个中文字完成当前问题。')+'''
   content=[{'type':'text','text':json.dumps({'question':data['answerContext'],'references':data['references']},ensure_ascii=False)}]
   for image in data['images']:
    if not image['dataUrl'].startswith('data:image/png;base64,'):raise ValueError('Invalid original image')
    content.extend([{'type':'text','text':json.dumps({k:image[k] for k in ('id','rank','caption')},ensure_ascii=False)},{'type':'image_url','image_url':{'url':image['dataUrl']}}])
   model=self.vision_model
  else:
   system=data['textPrompt']+"\\n只按以下格式输出，不输出think或标签外内容：<final_answer>Markdown中文答案</final_answer><used_figures>[]</used_figures>。答案正文不需要JSON转义，引用仅使用本轮提供的片段编号。"
   content=data['answerContext'];model=self.text_model
  is_exam=data.get('taskType') in ('exam','case')
  is_essay=data.get('taskType')=='essay'
  if is_essay:
   if data['images'] or question_images:raise ValueError('Unexpected essay image')
   task=validate_essay_task(data.get('essayTask'))
   system=essay_system(task['kind']);model=self.text_model
   material=[{'citation':'[片段'+str(r['rank'])+']','source':r['label'],'content':r['content']} for r in data['references']]
   content=json.dumps({'training':task,'textbookMaterials':material},ensure_ascii=False)
  if is_exam:
   system=exam_system(data['answerContext'],data.get('taskType')=='case')
   material=[{'citation':'[片段'+str(r['rank'])+']','source':r['label'],'content':r['content']} for r in data['references']]
   question=json.dumps({'question':data['answerContext'],'materials':material},ensure_ascii=False)
   if not data['images']:
    content=question
   else:content[0]={'type':'text','text':question}
   if question_images:system+='\\n用户截图是原题条件，不是教材出处；以用户核对后的文字为题干和选项，原图补充图表、公式。若文字与原图矛盾则说明并请求确认，不能忽略原图直接推断。用户截图不能列入used_figures或伪造教材页码。'
  if data.get('taskType')=='recognize':
   if not question_images:raise ValueError('No screenshot supplied')
   system='''+repr(RECOGNITION_SYSTEM)+''';content='只转录当前图片中的同一道题。'
  if question_images:
   if isinstance(content,str):content=[{'type':'text','text':content}]
   for i,image in enumerate(question_images):content.extend([{'type':'text','text':'用户题目截图'+str(i+1)+'（原题条件，不是教材引用）'},{'type':'image_url','image_url':{'url':image['dataUrl']}}])
   model=self.vision_model
  ids=[i['id'] for i in data['images']];ranks=[r['rank'] for r in data['references']]
  system+='\\n允许引用的教材片段编号：'+json.dumps(ranks)+'。used_figures只能填写下列教材原图id原样字符串或空数组：'+json.dumps(ids)+'。用户截图没有教材id，绝不能写入used_figures。不要填写图号、片段号或图片名称。'
  deadline=asyncio.get_running_loop().time()+max(1,min(180,data['timeoutSeconds']))
  for attempt in range(2):
   result=await asyncio.wait_for(model.ainvoke([SystemMessage(content=system),HumanMessage(content=content)]),timeout=max(0.1,deadline-asyncio.get_running_loop().time()))
   if data.get('taskType')=='recognize':return Message(text=json.dumps(parse_recognition(result.content),ensure_ascii=False))
   try:
    parsed=json.loads(serialize_generation(result.content,ids,ranks,is_exam or is_essay))
    parsed=reconcile_sources(parsed,data['references'],ids)
    if is_exam and (data.get('taskType')=='case' or question_kind(data['answerContext'])!='choice'):parsed['practice']=None
    if is_essay:parsed.pop('practice',None)
    return Message(text=json.dumps(parsed,ensure_ascii=False))
   except ValueError as error:
    recoverable=isinstance(error,json.JSONDecodeError) or any(s in str(error) for s in ('Incomplete exam envelope','Incomplete answer envelope','Invalid answer JSON','Unknown figure','Unknown answer citation','Incomplete figure declaration','Unexpected answer output','Invalid visual answer','Invalid visual text','Invalid visual response type'))
    if attempt or not recoverable or deadline-asyncio.get_running_loop().time()<8:raise
    system+='\\n上一次输出的格式或来源标记未通过校验。请对同一个问题和同一份资料重新简洁作答，完整闭合final_answer与used_figures，严格使用上方允许的片段编号和原图id。如果本轮要求practice则写null；未要求则不输出practice。普通文字答案必须写入final_answer，不得输出标签外文字或直接裸输出Markdown。资料未解释所问概念时，在final_answer说明本次证据不足，不编造定义或引用。不得引用用户截图作为教材来源。'
'''
