"""Local-only bridge for one browser QA critique; production is never addressed."""
import json,time
from bridge import LocalFlow,request_json
endpoint='http://localhost:5173/api/textbook/bridge'
headers={'Authorization':'Bearer local-test'}
def cloud(body):return request_json(endpoint,body,headers,timeout=15)
cloud({'action':'heartbeat','ready':True,'critiqueReady':True})
print('Local critique bridge ready',flush=True)
for _ in range(60):
 cloud({'action':'heartbeat','ready':True,'critiqueReady':True})
 job=cloud({'action':'critiqueClaim'}).get('critique')
 if job:
  started=time.monotonic();result=LocalFlow().run_critique(job)
  assert cloud({'action':'critiqueComplete','id':job['id'],'lease':job['lease'],'result':result})['ok']
  print(json.dumps({'done':True,'id':job['id'],'elapsed':round(time.monotonic()-started,2),'valid_ranks':True},ensure_ascii=False),flush=True);break
 time.sleep(2)
else:raise RuntimeError('Local browser did not submit a critique')
