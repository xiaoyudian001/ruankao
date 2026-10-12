"""Local web API verification with an actual question, model and page delivery."""
import json,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
base='http://localhost:5173'
def call(path,body=None):
 raw=None if body is None else json.dumps(body).encode()
 req=Request(base+path,data=raw,headers={'Origin':base,'Content-Type':'application/json'})
 with urlopen(req,timeout=20) as response:
  data=response.read()
  return data if response.headers.get('Content-Type','').startswith('image/') else json.loads(data)
job=call('/api/textbook/chat',{'requestId':str(uuid.uuid4()),'question':'结合图12-2解释三层C/S与B/S结构，说明图中各层的交互，并给出教材出处。','retrievalMode':'default'})['job']
print('Web question queued',flush=True)
for _ in range(100):
 messages=call('/api/textbook/chat?sessionId='+job['session_id'])['messages']
 answer=next(m for m in messages if m['id']==job['id'])
 if answer['status']=='done':break
 assert answer['status']!='failed',answer.get('error')
 time.sleep(2)
else:raise TimeoutError('Question did not complete')
ref=next(r for r in answer['references'] if r.get('figures'));figure=ref['figures'][0]
assert figure['pdfPage']==427 and '412' in ref['label']
assert 'path' not in figure and 'content' not in ref
print('Actual visual answer and safe figure metadata received',flush=True)
payload={'jobId':job['id'],'rank':ref['rank'],'page':figure['pdfPage']}
source=call('/api/textbook/source',payload)
from urllib.parse import urlencode
for _ in range(35):
 image=call('/api/textbook/source?'+urlencode(payload))
 if isinstance(image,bytes):break
 assert image.get('status')!='failed',image
 time.sleep(2)
else:raise TimeoutError('Original page not ready')
assert image[:2]==b'\xff\xd8' and len(image)>10000
record={'success':True,'jobId':job['id'],'sessionId':job['session_id'],'figure':figure,'pageImageBytes':len(image),'answer':answer['answer']}
Path('F:/daily/output/sysarch-figure-rag/web-api-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='answer'},ensure_ascii=False))
