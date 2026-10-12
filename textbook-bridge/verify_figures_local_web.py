"""One local browser QA question and original-page delivery; no production queue."""
import json,time,threading
from bridge import LocalFlow,request_json
from figures import try_enrich_answer
from pages import PageRenderer
from urllib.request import Request,urlopen
endpoint='http://localhost:5173/api/textbook/bridge'
headers={'Authorization':'Bearer local-test'}
stop=threading.Event()
def cloud(body):return request_json(endpoint,body,headers,timeout=15)
def pages():
 renderer=PageRenderer()
 while not stop.is_set():
  task=cloud({'action':'pageClaim'}).get('page')
  if task:
   raw=renderer.render(task['page'])
   req=Request('http://localhost:5173/api/textbook/page-upload',data=raw,method='PUT',headers={**headers,'Content-Type':'image/jpeg','X-Pdf-Page':str(task['page']),'X-Page-Lease':task['lease']})
   with urlopen(req,timeout=25) as response:assert json.load(response)['ok']
   print('Original page ready: '+str(task['page']),flush=True)
  stop.wait(1)
threading.Thread(target=pages,daemon=True).start()
cloud({'action':'heartbeat','ready':True,'modes':['default','complete'],'conversationReady':True,'sourcesReady':True})
print('Local figure question bridge ready',flush=True)
done=False
try:
 for _ in range(150):
  cloud({'action':'heartbeat','ready':True,'modes':['default','complete'],'conversationReady':True,'sourcesReady':True})
  if not done:
   job=cloud({'action':'claim'}).get('job')
   if job:
    start=time.monotonic();local=LocalFlow();text=local.run_conversation(job)
    result=try_enrich_answer(local,job,text,max(0,220-(time.monotonic()-start)))
    assert any(r.get('figures') for r in result['references']),'Real figure not adopted'
    assert cloud({'action':'complete','id':job['id'],'lease':job['lease'],**result,'elapsedMs':int((time.monotonic()-start)*1000)})['ok']
    print(json.dumps({'done':True,'elapsed':round(time.monotonic()-start,2),'figureCount':sum(len(r.get('figures',[])) for r in result['references'])}),flush=True);done=True
  time.sleep(2)
finally:stop.set()
