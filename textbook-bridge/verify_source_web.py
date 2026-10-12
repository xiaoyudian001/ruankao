"""Focused local integration: real saved Langflow output -> source queue -> private page."""
import hashlib,http.cookiejar,json,urllib.request,urllib.error,uuid
from pathlib import Path
from pages import PageRenderer

BASE='http://localhost:5173'
jar=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def call(path,body=None,connector=False,method=None,raw=None,extra=None,anonymous=False):
    headers={'Content-Type':'application/json','Origin':BASE,**(extra or {})}
    if connector:headers['Authorization']='Bearer local-preview-secret'
    data=raw if raw is not None else json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    try:
        with (urllib.request.urlopen(req,timeout=40) if anonymous else opener.open(req,timeout=40)) as response:
            content=response.read();ct=response.headers.get('Content-Type','')
            return response.status, json.loads(content) if 'json' in ct else content
    except urllib.error.HTTPError as error:return error.code,json.load(error)

with opener.open(BASE+'/signin-with-chatgpt?return_to=%2Ftextbook',timeout=40) as r:assert r.status==200
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':True,'modes':['default','complete'],'conversationReady':True,'sourcesReady':True},True)[0]==200
question={'question':'MTBF是什么？请指出教材出处。','requestId':str(uuid.uuid4())}
status,submitted=call('/api/textbook/chat',question);assert status==202,(status,submitted)
job=call('/api/textbook/bridge',{'action':'claim'},True)[1]['job'];assert job['id']==question['requestId']
actual=json.loads(Path(r'F:\daily\output\sysarch-citation-viewer\flow-verification.json').read_text(encoding='utf-8'))
assert actual['references']
assert call('/api/textbook/bridge',{'action':'complete','id':job['id'],'lease':job['lease'],**actual,'retrievalQuery':question['question'],'rewriteRoute':'direct'},True)[0]==200
message=call('/api/textbook/chat?sessionId='+job['session_id'])[1]['messages'][-1]
assert len(message['references'])==len(actual['references']) and 'content' not in message['references'][0]
ref=next(r for r in actual['references'] if 323 in r['pdfPages'])
selected={'jobId':job['id'],'rank':ref['rank'],'page':323}
assert call('/api/textbook/source',selected,anonymous=True)[0]==403
assert call('/api/textbook/source',{**selected,'page':728})[0]==404
assert call('/api/textbook/source',{**selected,'jobId':str(uuid.uuid4())})[0]==404
status,value=call('/api/textbook/source',selected);assert status==200,(status,value)
assert value['reference']['content']==ref['content']
task=call('/api/textbook/bridge',{'action':'pageClaim'},True)[1]['page']
image=PageRenderer().render(323)
if task:
    assert task['page']==323
    assert call('/api/textbook/page-upload',connector=True,method='PUT',raw=image,extra={'Content-Type':'image/jpeg','X-Pdf-Page':'323','X-Page-Lease':str(uuid.uuid4())})[0]==409
    assert call('/api/textbook/page-upload',connector=True,method='PUT',raw=image,extra={'Content-Type':'image/jpeg','X-Pdf-Page':'323','X-Page-Lease':task['lease']})[0]==200
query='?jobId='+job['id']+'&rank='+str(ref['rank'])+'&page=323'
assert call('/api/textbook/source'+query,anonymous=True)[0]==403
status,rendered=call('/api/textbook/source'+query);assert status==200 and hashlib.sha256(rendered).digest()==hashlib.sha256(image).digest()
report={'passed':True,'environment':'local_preview','session_id':job['session_id'],'job_id':job['id'],
        'actual_snapshot_preserved':True,'anonymous_read_rejected':True,'outside_reference_page_rejected':True,
        'unknown_job_rejected':True,'stale_upload_rejected':bool(task),'private_page_read_identical':True,
        'rank':ref['rank'],'pdf_page':323,'jpeg_bytes':len(image)}
Path(r'F:\daily\output\sysarch-citation-viewer\web-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
