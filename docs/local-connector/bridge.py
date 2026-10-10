"""Outbound-only connector for one fixed, existing Langflow flow."""
import json, logging, msvcrt, re, sys, threading, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

FLOW='2e38f267-52d8-484f-bc4a-81ad7a2e3436'
FLOW_MODES={'default':FLOW,'complete':'ce82698e-54b8-4360-8a11-6f6c4f43f5ff'}
BASE='http://127.0.0.1:7860/api/v1'
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'sysarch-fullbook'))
from conversation_rewrite import prepare_rewrite, validate_rewrite, bounded_history, encode_history, CLARIFY
from critique import parse_result,encode_payload,critique_text
CONVERSATION_FLOWS={'rewrite':'61c7f5f7-90b8-49cd-bc25-20b6168586db',
                    'default':'94e0161b-b811-46e4-807a-c5a4c5f05806',
                    'complete':'f237233c-36bb-4d47-9f3b-fc456b911edb'}

def flow_for_mode(mode):
    if mode is None:mode='default'
    if mode not in FLOW_MODES:raise ValueError('Unsupported retrieval mode')
    return FLOW_MODES[mode]

def clean_answer(text):
    return re.sub(r'<think\b[^>]*>.*?(?:</think\s*>|$)','',text,flags=re.I|re.S).strip()

def answer_text(result):
    for group in result.get('outputs',[]):
        for output in group.get('outputs',[]):
            for message in output.get('results',{}).values():
                if isinstance(message,dict):
                    text=message.get('text') or message.get('data',{}).get('text')
                    if isinstance(text,str) and clean_answer(text):return clean_answer(text)
    raise ValueError('Empty final answer')

def answer_payload(result):
    text=answer_text(result)
    for group in result.get('outputs',[]):
        for output in group.get('outputs',[]):
            for message in output.get('results',{}).values():
                if isinstance(message,dict):
                    value=message.get('text') or message.get('data',{}).get('text')
                    if isinstance(value,str) and clean_answer(value)==text:
                        metadata=message.get('session_metadata') or message.get('data',{}).get('session_metadata') or {}
                        refs=metadata.get('textbook_refs',[]) if isinstance(metadata,dict) else []
                        return {'answer':text,'references':refs if isinstance(refs,list) else []}
    return {'answer':text,'references':[]}

def request_json(url,body=None,headers=None,timeout=20):
    data=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
    req=Request(url,data=data,headers={'Content-Type':'application/json','User-Agent':'TextbookConnector/1.0',**(headers or {})})
    with urlopen(req,timeout=timeout) as response:return json.load(response)

class LocalFlow:
    def __init__(self):self.token=None
    def call(self,path,body=None,timeout=20,retry=True):
        if not self.token:self.token=request_json(BASE+'/auto_login')['access_token']
        try:return request_json(BASE+path,body,{'Authorization':'Bearer '+self.token},timeout)
        except HTTPError as error:
            if error.code==401 and retry:
                self.token=None;return self.call(path,body,timeout,retry=False)
            raise
    def ready(self,mode='default'):
        try:
            flow=self.call('/flows/'+flow_for_mode(mode))
            nodes=flow['data']['nodes']
            knowledge=next(n for n in nodes if n['id']=='Knowledge-Y8gm2')
            if knowledge['data']['node']['template']['knowledge_base']['value']!='SysArchTutorRAGv3':return False
            tags=request_json('http://127.0.0.1:11434/api/tags',timeout=5)
            return any(x.get('name')=='bge-m3:latest' for x in tags.get('models',[]))
        except Exception:return False
    def run(self,job):
        return self.run_with_sources(job)['answer']

    def critique_ready(self):
        try:
            state=json.loads((ROOT/'critique-flow.json').read_text(encoding='utf-8'))
            flow=self.call('/flows/'+state['flow_id'])
            return any(n['id']=='RecallCritique-SysArch' for n in flow['data']['nodes'])
        except Exception:return False

    def run_critique(self,job):
        state=json.loads((ROOT/'critique-flow.json').read_text(encoding='utf-8'))
        body={'input_request':{'input_value':encode_payload({k:job[k] for k in ('front','back','response','references_json')}),
              'input_type':'chat','output_type':'any','output_component':'RecallCritique-SysArch','session_id':'critique-'+job['id'],
              'tweaks':{'ChatInput-z2rit':{'should_store_message':False}}}}
        text=critique_text(self.call('/run/session/'+state['flow_id'],body,timeout=130))
        refs=json.loads(job['references_json']) if isinstance(job['references_json'],str) else job['references_json']
        return parse_result(text,[r['rank'] for r in refs])

    def run_with_sources(self,job):
        body={'input_request':{'input_value':job['question'],'input_type':'chat','output_type':'chat',
              'output_component':'ChatOutput-QRg8s','session_id':'web-'+job['session_id'],
              'tweaks':{'ChatInput-z2rit':{'should_store_message':False},'ChatOutput-QRg8s':{'should_store_message':False}}}}
        flow_id=flow_for_mode(job.get('retrieval_mode'))
        return answer_payload(self.call('/run/session/'+flow_id,body,timeout=210))

    def conversation_ready(self):
        try:
            for mode,fid in CONVERSATION_FLOWS.items():
                flow=self.call('/flows/'+fid)
                ids={n['id'] for n in flow['data']['nodes']}
                required='ConversationRewrite-SysArch' if mode=='rewrite' else 'ConversationAnswerContext-SysArch'
                if required not in ids:return False
            return True
        except Exception:return False

    def run_conversation(self,job):
        mode=job.get('retrieval_mode') or 'default';flow_for_mode(mode)
        history=bounded_history(job.get('history_json','[]'))
        plan=prepare_rewrite(job['question'],history)
        history_json=encode_history(history)
        if plan['route']=='pending':
            try:
                body={'input_request':{'input_value':job['question'],'input_type':'chat','output_type':'any',
                    'output_component':'ConversationRewrite-SysArch','session_id':'rewrite-'+job['session_id'],
                    'tweaks':{'ChatInput-z2rit':{'should_store_message':False},'ConversationRewrite-SysArch':{'history_json':history_json}}}}
                output=self.call('/run/session/'+CONVERSATION_FLOWS['rewrite'],body,timeout=40)
                result=next(o['outputs']['rewrite_result']['message'] for group in output['outputs'] for o in group['outputs'] if 'rewrite_result' in o.get('outputs',{}))
                plan=validate_rewrite(plan,json.dumps({'query':result['query'],'needs_clarification':result['route']=='clarification'},ensure_ascii=False))
            except Exception:
                plan={**plan,'query':'','route':'clarification'}
        if plan['route']=='clarification':answer={'answer':CLARIFY,'references':[]}
        elif not history:answer=self.run_with_sources(job)
        else:
            body={'input_request':{'input_value':plan['query'],'input_type':'chat','output_type':'chat',
                'output_component':'ChatOutput-QRg8s','session_id':'web-'+job['session_id'],
                'tweaks':{'ChatInput-z2rit':{'should_store_message':False},'ChatOutput-QRg8s':{'should_store_message':False},
                    'ConversationAnswerContext-SysArch':{'original_question':job['question'],'history_json':history_json}}}}
            answer=answer_payload(self.call('/run/session/'+CONVERSATION_FLOWS[mode],body,timeout=185))
        return {**answer,'retrievalQuery':plan['query'],'rewriteRoute':plan['route']}

def main():
    config=json.loads(sys.stdin.readline());sys.stdin.close()
    site=config['site_url'].rstrip('/')
    if site!='https://ruankao-40-day.xiaoydian.chatgpt.site':raise ValueError('Unexpected site')
    logging.basicConfig(filename=ROOT/'bridge.log',level=logging.INFO,format='%(asctime)s %(message)s',encoding='utf-8')
    lock=open(ROOT/'bridge.lock','a+b');lock.seek(0);lock.write(b'1');lock.flush();lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:return
    headers={'Authorization':'Bearer '+config['secret']}
    stop=threading.Event();ready=threading.Event();sources_ready=threading.Event();critique_ready=threading.Event();local=LocalFlow()
    def cloud(body):return request_json(site+'/api/textbook/bridge',body,headers,timeout=20)
    def page_worker():
        try:
            from pages import PageRenderer
            renderer=PageRenderer();sources_ready.set()
        except Exception as error:
            logging.info('Original page renderer unavailable: %s',type(error).__name__);return
        while not stop.is_set() and not (ROOT/'stop.flag').exists():
            task=None
            try:
                task=cloud({'action':'pageClaim'}).get('page')
                if not task:stop.wait(2);continue
                image=renderer.render(task['page'])
                uploaded=False
                for attempt in range(3):
                    try:
                        req=Request(site+'/api/textbook/page-upload',data=image,method='PUT',headers={**headers,
                            'Content-Type':'image/jpeg','User-Agent':'TextbookConnector/1.0',
                            'X-Pdf-Page':str(task['page']),'X-Page-Lease':task['lease']})
                        with urlopen(req,timeout=25) as response:result=json.load(response)
                        uploaded=result.get('ok') is True;break
                    except HTTPError as error:
                        if error.code==409:
                            # Delivery may have succeeded before a response was lost.
                            uploaded=True;break
                        if attempt==2:raise
                        stop.wait(2)
                    except Exception:
                        if attempt==2:raise
                        stop.wait(2)
                if not uploaded:raise ValueError('Page upload failed')
                logging.info('Original PDF page ready: %s',task['page'])
            except Exception as error:
                logging.info('Original page unavailable: %s HTTP=%s',type(error).__name__,getattr(error,'code','n/a'))
                if task:
                    try:cloud({'action':'pageFail','page':task['page'],'lease':task['lease']})
                    except Exception:pass
                stop.wait(5)
    threading.Thread(target=page_worker,daemon=True).start()
    def heartbeat():
        while not stop.is_set():
            modes=[mode for mode in FLOW_MODES if local.ready(mode)]
            available='default' in modes
            if available:ready.set()
            else:ready.clear()
            critique_available=local.critique_ready()
            if critique_available:critique_ready.set()
            else:critique_ready.clear()
            try:
                conversational=available and local.conversation_ready()
                cloud({'action':'heartbeat','ready':available,'modes':modes,'conversationReady':conversational,'sourcesReady':sources_ready.is_set(),'critiqueReady':critique_available})
                (ROOT/'status.json').write_text(json.dumps({'updated_at':int(time.time()),'local_ready':available,'connected':True,'modes':modes,'conversation_ready':conversational,'sources_ready':sources_ready.is_set(),'critique_ready':critique_available}),encoding='utf-8')
            except Exception as error:
                logging.info('Heartbeat unavailable: %s HTTP=%s',type(error).__name__,getattr(error,'code','n/a'))
                (ROOT/'status.json').write_text(json.dumps({'updated_at':int(time.time()),'local_ready':available,'connected':False}),encoding='utf-8')
            stop.wait(10)
    threading.Thread(target=heartbeat,daemon=True).start()
    logging.info('Connector started; whitelisted textbook modes, outbound HTTPS only')
    try:
        while not (ROOT/'stop.flag').exists():
            if not ready.is_set() and not critique_ready.is_set():stop.wait(4);continue
            is_critique=False
            try:
                job=cloud({'action':'claim'})['job'] if ready.is_set() else None
                if not job and critique_ready.is_set():
                    job=cloud({'action':'critiqueClaim'}).get('critique');is_critique=bool(job)
            except Exception as error:
                logging.info('Queue unavailable: %s HTTP=%s',type(error).__name__,getattr(error,'code','n/a'));stop.wait(6);continue
            if not job:stop.wait(3);continue
            start=time.monotonic();result={'action':'critiqueComplete' if is_critique else 'complete','id':job['id'],'lease':job['lease']}
            try:
                if is_critique:result['result']=local.run_critique(job)
                else:result.update(local.run_conversation(job))
            except Exception as error:
                logging.info('Flow failed %s: %s',job['id'],type(error).__name__)
                result['error']='AI 点评执行失败，请稍后重试。' if is_critique else '本地问答流程执行失败或超时，请检查 Langflow 和 Ollama 后重试。'
            result['elapsedMs']=int((time.monotonic()-start)*1000)
            # Retry only delivery of an already-generated result, never the model execution.
            for attempt in range(3):
                try:cloud(result);logging.info('Result delivered %s',job['id']);break
                except HTTPError as error:
                    if error.code==409:logging.info('Late result rejected %s',job['id']);break
                    stop.wait(2*(attempt+1))
                except Exception:stop.wait(2*(attempt+1))
    finally:
        stop.set()
        try:cloud({'action':'heartbeat','ready':False})
        except Exception:pass
        lock.close()
        logging.info('Connector stopped')

if __name__=='__main__':main()
