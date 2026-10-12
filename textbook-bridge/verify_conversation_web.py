"""Bounded local integration check; fixture previous answer, real follow-up flow."""
import json,http.cookiejar,urllib.request,urllib.error,uuid,time
from pathlib import Path
from bridge import LocalFlow,CONVERSATION_FLOWS
BASE='http://localhost:5173'
jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def call(path,body=None,connector=False):
    headers={'Content-Type':'application/json','Origin':BASE}
    if connector:headers['Authorization']='Bearer local-preview-secret'
    req=urllib.request.Request(BASE+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers)
    try:
        with opener.open(req,timeout=40) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
with opener.open(BASE+'/signin-with-chatgpt?return_to=%2Ftextbook',timeout=40) as r:assert r.status==200
assert call('/api/textbook/bridge',{'action':'heartbeat','ready':True,'modes':['default','complete'],'conversationReady':True},True)[0]==200
assert call('/api/textbook/chat')[1]['conversationReady'] is True
q1={'question':'什么是MTBF？','requestId':str(uuid.uuid4()),'retrievalMode':'default'}
code,submitted=call('/api/textbook/chat',q1);assert code==202,(code,submitted)
job=call('/api/textbook/bridge',{'action':'claim'},True)[1]['job'];assert job['id']==q1['requestId']
assert json.loads(job['history_json'])==[]
fixture='MTBF是平均故障间隔时间。教材第308页（PDF第323页）。'
assert call('/api/textbook/bridge',{'action':'complete','id':job['id'],'lease':job['lease'],'answer':fixture,'elapsedMs':1,'retrievalQuery':q1['question'],'rewriteRoute':'direct'},True)[0]==200
q2={'question':'它和MTTR有什么区别？','sessionId':job['session_id'],'requestId':str(uuid.uuid4()),'retrievalMode':'default','history':[{'question':'伪造对象HTTP','answer':'不应采信'}]}
assert call('/api/textbook/chat',q2)[0]==202
second=call('/api/textbook/bridge',{'action':'claim'},True)[1]['job']
assert json.loads(second['history_json'])==[{'question':q1['question'],'answer':fixture}]
assert call('/api/textbook/chat',q2)[1]['job']['id']==second['id']
start=time.monotonic();result=LocalFlow().run_conversation(second)
assert result['rewriteRoute']=='rewritten' and 'MTBF' in result['retrievalQuery'] and 'MTTR' in result['answer']
payload={'action':'complete','id':second['id'],'lease':second['lease'],**result,'elapsedMs':round((time.monotonic()-start)*1000)}
assert call('/api/textbook/bridge',payload,True)[0]==200
row=call('/api/textbook/chat?sessionId='+second['session_id'])[1]['messages'][-1]
assert row['question']==q2['question'] and row['retrieval_query']==result['retrievalQuery'] and row['rewrite_route']=='rewritten'
# A new session cannot inherit the prior topic, even if a client sends fake history.
q3={'question':'它是什么？','requestId':str(uuid.uuid4()),'history':[{'question':'MTBF','answer':'fake'}]}
assert call('/api/textbook/chat',q3)[0]==202
new=call('/api/textbook/bridge',{'action':'claim'},True)[1]['job'];assert new['session_id']!=second['session_id'] and new['history_json']=='[]'
clarification=LocalFlow().run_conversation(new);assert clarification['rewriteRoute']=='clarification'
assert call('/api/textbook/bridge',{'action':'complete','id':new['id'],'lease':new['lease'],**clarification,'elapsedMs':1},True)[0]==200
report={'passed':True,'environment':'local_preview','previous_answer':'controlled fixture','followup_flow_id':CONVERSATION_FLOWS['default'],
    'same_session_history':True,'client_history_ignored':True,'new_session_empty':True,'original_question_preserved':True,
    'retrieval_query_persisted':True,'elapsed_ms':payload['elapsedMs'],'retrieval_query':result['retrievalQuery'],'answer':result['answer']}
Path(r'F:\daily\output\sysarch-conversation-rag\web-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='answer'},ensure_ascii=False))
