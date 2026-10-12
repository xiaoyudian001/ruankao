"""Verify the real web queue through local preview and the fixed local complete flow."""
import json, http.cookiejar, urllib.request, urllib.error, uuid, time
from pathlib import Path
from bridge import LocalFlow

BASE='http://localhost:5173'
jar=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def call(path,body=None,connector=False,auth=True):
    headers={'Content-Type':'application/json','Origin':BASE}
    if connector:headers['Authorization']='Bearer local-preview-secret'
    req=urllib.request.Request(BASE+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers)
    try:
        with (opener.open if auth else urllib.request.urlopen)(req,timeout=40) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)

assert call('/api/textbook/chat',auth=False)[0]==403
with opener.open(BASE+'/signin-with-chatgpt?return_to=%2Ftextbook',timeout=40) as r:assert r.status==200
request={'question':'结构模型与框架模型有什么区别？依据教材比较描述重点。',
         'requestId':str(uuid.uuid4()),'retrievalMode':'complete'}
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':True},connector=True)[0]==200
assert call('/api/textbook/chat',request)[0]==503
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':True,'modes':['default','complete']},connector=True)[0]==200
state=call('/api/textbook/chat')[1]
assert state['availableModes']==['default','complete']
assert call('/api/textbook/chat',{**request,'retrievalMode':'arbitrary-flow-id'})[0]==400
status,result=call('/api/textbook/chat',request)
assert status==202,(status,result)
assert call('/api/textbook/chat',request)[1]['job']['id']==result['job']['id']
assert call('/api/textbook/chat',{**request,'retrievalMode':'default'})[0]==409
status,claimed=call('/api/textbook/bridge',{'action':'claim'},connector=True)
assert status==200
job=claimed['job']
assert job['id']==result['job']['id'] and job['retrieval_mode']=='complete'
start=time.monotonic()
answer=LocalFlow().run(job)
assert answer and '<think>' not in answer and '结构模型' in answer and '框架模型' in answer
payload={'action':'complete','id':job['id'],'lease':job['lease'],'answer':answer,'elapsedMs':int((time.monotonic()-start)*1000)}
assert call('/api/textbook/bridge',payload,connector=True)[0]==200
assert call('/api/textbook/bridge',payload,connector=True)[0]==409
history=call('/api/textbook/chat?sessionId='+job['session_id'])[1]['messages']
assert history[0]['status']=='done' and history[0]['retrieval_mode']=='complete' and history[0]['answer']==answer
report={'passed':True,'mode':'complete','flow_id':'ce82698e-54b8-4360-8a11-6f6c4f43f5ff',
        'auth_rejected':True,'unavailable_mode_rejected':True,'invalid_mode_rejected':True,
        'idempotency_mode_conflict_rejected':True,'claimed_mode_preserved':True,'history_mode_preserved':True,
        'elapsed_ms':payload['elapsedMs'],'answer':answer,'environment':'local_preview'}
dest=Path(r'F:\daily\output\sysarch-complete-rag\web-local-verification.json')
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='answer'},ensure_ascii=False))
