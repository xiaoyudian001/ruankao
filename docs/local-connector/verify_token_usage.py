"""Two bounded real calls with self-authored text; only metadata is printed."""
import json,sys,uuid
from pathlib import Path
sys.path.insert(0,'F:/daily/sysarch-fullbook')
from bridge import LocalFlow
from streaming import Mailbox

def main():
 api=LocalFlow();results=[]
 for stream in (False,True):
  job={'id':str(uuid.uuid4()),'lease':str(uuid.uuid4()),'task_type':'qa'};box=Mailbox(job['id'],job['lease']) if stream else None
  if box:job['_stream']=type('Check',(),{'check':lambda self:None})()
  try:
   answer=api.generate_evidence(job,{'references':[],'textPrompt':'测试材料：幂等是对相同请求执行一次或多次，系统产生相同预期效果。只简要解释这一概念。'},'用两句话解释幂等，并给出一个接口例子。',[],{},80)
   usage=answer.get('tokenUsage');assert usage and usage['reportedCalls']>=1 and usage['inputTokens']>0 and usage['outputTokens']>0
   assert '<think>' not in answer['answer']
   results.append({'stream':stream,'tokenUsage':usage,'answerLength':len(answer['answer'])})
  finally:
   if box:box.cleanup()
 Path('F:/daily/output/token-usage').mkdir(parents=True,exist_ok=True)
 Path('F:/daily/output/token-usage/real-model.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
