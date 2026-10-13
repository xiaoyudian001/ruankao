"""Private per-lease mailbox: visible answer snapshots and cooperative cancellation."""
import asyncio,json,os,re,shutil,tempfile,time,uuid,threading
from pathlib import Path

class GenerationStopped(Exception):pass

def visible_answer(raw,kind):
 text=re.sub(r'<think\b[^>]*>.*?(?:</think\s*>|$)','',raw,flags=re.I|re.S)
 def section(tag):
  match=re.search(r'<'+tag+r'>',text,re.I)
  if not match:return ''
  return text[match.end():].split('<',1)[0].replace('>','').strip()[:60000]
 main=section('final_answer')
 if kind=='qa_fallback' and main:return '**AI 知识补充**：以下为通用知识，非教材原文；未联网核实。\n\n'+main
 if kind=='qa_mixed':
  extra=section('ai_supplement')
  return ('## 教材依据\n\n'+main if main else '')+('\n\n## AI 知识补充\n\n以下为通用知识，非教材原文；未联网核实。\n\n'+extra if extra else '')
 return main

class Mailbox:
 def __init__(self,job_id,lease,root=None,create=True):
  for value in (job_id,lease):
   if not isinstance(value,str) or str(uuid.UUID(value))!=value.lower():raise ValueError('Invalid stream identity')
  self.directory=Path(root or Path(tempfile.gettempdir())/'ruankao-answer-stream-v1')/(job_id+'-'+lease)
  if create:self.directory.mkdir(parents=True,exist_ok=True)
  elif not self.directory.is_dir():raise GenerationStopped('Stream mailbox expired')
 def read(self):
  try:
   value=json.loads((self.directory/'progress.json').read_text(encoding='utf-8'))
   if isinstance(value.get('seq'),int) and isinstance(value.get('text'),str):return value
  except (OSError,ValueError):pass
  return {'seq':0,'text':''}
 def publish(self,text):
  if self.cancelled():raise GenerationStopped('Generation stopped')
  if not isinstance(text,str) or '<' in text or '>' in text:raise ValueError('Invalid stream text')
  value={'seq':self.read()['seq']+1,'text':text[:60000]};temp=self.directory/(str(uuid.uuid4())+'.tmp')
  try:temp.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');os.replace(temp,self.directory/'progress.json')
  finally:temp.unlink(missing_ok=True)
 def cancel(self):
  if self.directory.is_dir():(self.directory/'stop').touch()
 def cancelled(self):return not self.directory.is_dir() or (self.directory/'stop').exists()
 def cleanup(self):shutil.rmtree(self.directory,ignore_errors=True)

async def consume_model(model,messages,box,kind):
 raw='';last='';published=0.;box.publish('')
 # Recent LangChain treats an explicitly set streaming=False as a hard
 # opt-out, even for astream(). Copy the handle for this answer only.
 if getattr(model,'streaming',None) is False and hasattr(model,'model_copy'):model=model.model_copy(update={'streaming':True})
 options={'extra_body':{'reasoning_split':True}} if str(getattr(model,'model_name','')).startswith('MiniMax') else {}
 iterator=model.astream(messages,**options).__aiter__();next_chunk=None
 try:
  while True:
   if box.cancelled():raise GenerationStopped('Generation stopped')
   if next_chunk is None:next_chunk=asyncio.create_task(anext(iterator))
   done,_=await asyncio.wait({next_chunk},timeout=.2)
   if not done:continue
   try:chunk=next_chunk.result()
   except StopAsyncIteration:break
   finally:next_chunk=None
   content=chunk.content
   if isinstance(content,list):content=''.join(p.get('text','') for p in content if isinstance(p,dict) and p.get('type')=='text')
   if isinstance(content,str):raw+=content
   if len(raw)>200000:raise ValueError('Stream answer budget exceeded')
   text=visible_answer(raw,kind)[:60000]
   if text!=last and time.monotonic()-published>=.3:box.publish(text);last=text;published=time.monotonic()
  text=visible_answer(raw,kind)[:60000]
  if text!=last:box.publish(text)
  return raw
 finally:
  if next_chunk is not None:
   next_chunk.cancel()
   try:await next_chunk
   except (asyncio.CancelledError,StopAsyncIteration):pass
  close=getattr(iterator,'aclose',None)
  if close:await close()

class StreamMonitor:
 def __init__(self,job,cloud):
  self.job=job;self.cloud=cloud;self.box=Mailbox(job['id'],job['lease']);self.done=threading.Event();self.sent=0;self.thread=None
 def sync(self):
  snapshot=self.box.read();payload={'action':'progress',**snapshot} if snapshot['seq']>self.sent else {'action':'control'}
  try:
   result=self.cloud({**payload,'id':self.job['id'],'lease':self.job['lease']})
   if result.get('cancelRequested'):self.box.cancel()
   if payload['action']=='progress':self.sent=snapshot['seq']
  except Exception as error:
   if getattr(error,'code',None)==409:self.box.cancel()
 def start(self):
  def run():
   while not self.done.is_set():self.sync();self.done.wait(1)
  self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
 def close(self):
  # Completion has priority over monitor I/O. An already-running bounded
  # request may finish in its daemon thread; terminal/lease guards reject it.
  self.done.set()
 def check(self):
  if self.box.cancelled():raise GenerationStopped('Generation stopped')
