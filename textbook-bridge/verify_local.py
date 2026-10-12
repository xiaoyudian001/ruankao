import json, http.cookiejar, urllib.request, urllib.error, uuid, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from bridge import LocalFlow
BASE='http://localhost:5173'
jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def call(path,body=None,connector=False,auth=True):
    headers={'Content-Type':'application/json','Origin':BASE}
    if connector:headers['Authorization']='Bearer local-preview-secret'
    req=urllib.request.Request(BASE+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers)
    try:
        with (opener.open if auth else urllib.request.urlopen)(req,timeout=30) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)

assert call('/api/textbook/chat',auth=False)[0]==403
with opener.open(BASE+'/signin-with-chatgpt?return_to=%2Ftextbook',timeout=30) as r:assert r.status==200
assert call('/api/textbook/bridge',{'action':'claim'},auth=False)[0]==401
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':False},connector=True)[0]==200
question='解释一下什么是MTBF，并指出在教材的哪一页。'
request={'question':question,'requestId':str(uuid.uuid4())}
assert call('/api/textbook/chat',request)[0]==503
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':True},connector=True)[0]==200
status,result=call('/api/textbook/chat',request);assert status==202,(status,result)
assert call('/api/textbook/chat',request)[1]['job']['id']==result['job']['id']
status,claimed=call('/api/textbook/bridge',{'action':'claim'},connector=True);assert status==200
job=claimed['job'];assert job['id']==result['job']['id']
assert call('/api/textbook/bridge',{'action':'claim'},connector=True)[1]['job'] is None
start=time.monotonic();answer=LocalFlow().run(job);elapsed=int((time.monotonic()-start)*1000)
assert '<think>' not in answer and '教材第308页（PDF第323页）' in answer,answer
payload={'action':'complete','id':job['id'],'lease':str(uuid.uuid4()),'answer':answer,'elapsedMs':elapsed}
assert call('/api/textbook/bridge',payload,connector=True)[0]==409
payload['lease']=job['lease'];assert call('/api/textbook/bridge',payload,connector=True)[0]==200
assert call('/api/textbook/bridge',payload,connector=True)[0]==409
status,data=call('/api/textbook/chat?sessionId='+job['session_id']);assert status==200
assert data['messages'][0]['status']=='done' and data['messages'][0]['answer']==answer
report={'passed':True,'anonymous_rejected':True,'bridge_auth_separated':True,'offline_rejected':True,'duplicate_request_deduplicated':True,'one_active_job':True,'stale_delivery_rejected':True,'persisted_answer':True,'dual_pages_correct':True,'elapsed_ms':elapsed,'answer':answer}
Path(__file__).with_name('local-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='answer'},ensure_ascii=False))
