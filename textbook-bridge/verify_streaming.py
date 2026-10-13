"""Real existing-model test with self-authored notes; no website conversation records."""
import concurrent.futures,json,time,uuid,sys
from pathlib import Path
from bridge import LocalFlow
from streaming import Mailbox

def main():
 local=LocalFlow();records=[]
 for cancel in ((True,) if '--cancel-only' in sys.argv else (False,True)):
  job={'id':str(uuid.uuid4()),'lease':str(uuid.uuid4()),'task_type':'qa'};box=Mailbox(job['id'],job['lease'])
  class Control:
   def check(self):
    if box.cancelled():raise RuntimeError('Stopped')
  job['_stream']=Control();snapshot={'textPrompt':'你是教学助手，根据以下自写实验资料解释：缓存减少重复计算，但需要处理缓存失效。请用中文详细解释并给出多个自写示例。仅引用片段1。','references':[{'rank':1,'label':'自写实验资料','content':'缓存减少重复计算，但需要处理缓存失效。'}]}
  start=time.monotonic();first=None;seq=[];sent=False;model_started=None
  try:
   with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(local.generate_evidence,job,snapshot,'请写一份长篇教学说明，逐条解释缓存失效、过期时间、主动更新、延迟双删、版本键、事件失效、热键、雪崩、穿透、击穿等十个主题。每个主题至少100个中文字，给出场景、机制和代价。完整回答请超过1500个中文字。',[],{},100)
    while not future.done():
     value=box.read()
     if value['seq'] and model_started is None:model_started=time.monotonic()
     if value['text']:
      if first is None:first=round(time.monotonic()-start,2)
      if not seq or seq[-1]!=value['seq']:seq.append(value['seq'])
      assert '<think' not in value['text'] and '<final_answer' not in value['text']
     if cancel and not sent and first is not None:box.cancel();sent=True;cancel_at=time.monotonic()
     time.sleep(.15)
    if cancel:
     try:future.result();raise AssertionError('Cancelled generation unexpectedly completed')
     except Exception as error:
      if isinstance(error,AssertionError):raise
      delay=round(time.monotonic()-cancel_at,2) if sent else None
      detail=error.read().decode(errors='replace') if hasattr(error,'read') else str(error)
      record={'cancel':True,'firstBodySeconds':first,'stopSeconds':delay,'partialLength':len(box.read()['text']),'errorType':type(error).__name__,'stoppedMarker':'Generation stopped' in detail or 'GenerationStopped' in detail}
      print(json.dumps(record),flush=True)
      assert sent and delay<30 and record['stoppedMarker'],'Cancellation did not reach component'
      records.append(record)
    else:
     result=future.result();total=round(time.monotonic()-start,2);assert first is not None and first<total and result['answer'],'No incremental answer before completion'
     records.append({'cancel':False,'firstBodySeconds':first,'totalSeconds':total,'snapshotsObserved':len(seq),'answerLength':len(result['answer'])})
    print(json.dumps(records[-1]),flush=True)
  finally:box.cleanup()
 path=Path('F:/daily/output/answer-streaming/real-model-verification.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(records,indent=2),encoding='utf-8');print(json.dumps(records),flush=True)

if __name__=='__main__':main()
