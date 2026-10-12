"""Run unchanged QA logic via authenticated Langflow build/events API; persist resumable results."""
import argparse
import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from langflow_api import LangflowAPI, BASE

ROOT = Path(r'F:\daily\output\sysarch-rag-evaluation')
FLOW = '2e38f267-52d8-484f-bc4a-81ad7a2e3436'

def text_of(value):
    if isinstance(value,str): return value
    if isinstance(value,dict):
        for key in ('raw','text','message','repr'):
            if key in value:
                result=text_of(value[key])
                if result:return result
        if 'data' in value:return text_of(value['data'])
    return ''

def field(node,key):
    return node.get('data',{}).get('node',{}).get('template',{}).get(key,{}).get('value')

def flow_logic_fingerprint(data):
    logic=copy.deepcopy(data)
    logic.pop('viewport',None)
    for node in logic.get('nodes',[]):
        node.pop('position',None)
        node.pop('selected',None)
        node.get('data',{}).pop('selected',None)
        node.get('data',{}).get('node',{}).pop('last_updated',None)
    return hashlib.sha256(json.dumps(logic,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-name',default='baseline-20261008')
    parser.add_argument('--flow-id',default=FLOW)
    parser.add_argument('--retrieval-node',default='Knowledge-Y8gm2')
    parser.add_argument('--questions',default='',help='Optional comma-separated IDs for a separately named smoke run')
    args=parser.parse_args(); dest=ROOT/args.run_name;dest.mkdir(parents=True,exist_ok=True)
    dataset=json.loads((ROOT/'dataset.json').read_text(encoding='utf-8'))
    requested=set(filter(None,args.questions.split(',')))
    if requested-set(t['id'] for t in dataset['tests']):raise ValueError('Unknown question IDs')
    tests=[t for t in dataset['tests'] if not requested or t['id'] in requested]
    api=LangflowAPI();flow=api.call('/flows/'+args.flow_id)
    original=flow['data']; fingerprint=hashlib.sha256(json.dumps(original,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    logic_fingerprint=flow_logic_fingerprint(original)
    runflow=copy.deepcopy(original)
    for node in runflow['nodes']:
        for k in ('should_store_message',):
            template=node.get('data',{}).get('node',{}).get('template',{})
            if k in template:template[k]['value']=False
    nodes={n['id']:n for n in original['nodes']}
    config={'started_utc':datetime.now(timezone.utc).isoformat(),'flow_id':args.flow_id,'flow_name':flow['name'],
            'flow_sha256':fingerprint,'dataset_sha256':hashlib.sha256((ROOT/'dataset.json').read_bytes()).hexdigest(),
            'flow_logic_sha256':logic_fingerprint,
            'langflow_version':api.call('/version'),'knowledge_base':field(nodes['Knowledge-Y8gm2'],'knowledge_base'),
            'top_k':field(nodes[args.retrieval_node],'final_k') or field(nodes[args.retrieval_node],'top_k'),
            'dense_candidate_k':field(nodes['Knowledge-Y8gm2'],'top_k'),
            'retrieval_node':args.retrieval_node, 'metadata_filter':field(nodes['Knowledge-Y8gm2'],'metadata_filter'),
            'question_ids':[t['id'] for t in tests],
            'hybrid':{k:field(nodes.get('TextbookBM25-SysArch',{}),k) for k in ('candidate_k','snapshot_path','snapshot_sha256')},
            'temperature':field(nodes['LanguageModelComponent-BpTTF'],'temperature'),
            'model':field(nodes['LanguageModelComponent-BpTTF'],'model_name'),
            'prompt':field(nodes['Prompt Template-fzcHC'],'template'),
            'evaluation_mode':'20题单次顺序执行；独立session；测试副本仅关闭消息保存；未PATCH正式流程',
            'api':'authenticated /build/{flow_id}/flow + /build/{job_id}/events',
            'node_code_sha256':{k:hashlib.sha256(str(field(n,'code')).encode()).hexdigest() for k,n in nodes.items()}}
    cfg=dest/'configuration.json'
    if cfg.exists():
        old=json.loads(cfg.read_text(encoding='utf-8'))
        if old['flow_id']!=args.flow_id:raise RuntimeError('Flow ID changed; choose a new run-name')
        if old.get('retrieval_node','Knowledge-Y8gm2')!=args.retrieval_node:raise RuntimeError('Retrieval output changed; choose a new run-name')
        if old.get('flow_logic_sha256',old['flow_sha256'])!=(logic_fingerprint if 'flow_logic_sha256' in old else fingerprint):raise RuntimeError('Flow logic changed; choose a new run-name rather than mixing baselines')
        if old['dataset_sha256']!=config['dataset_sha256']:raise RuntimeError('Dataset changed; choose a new run-name rather than mixing test sets')
        if old.get('question_ids',[t['id'] for t in dataset['tests']])!=config['question_ids']:raise RuntimeError('Question subset changed; choose a new run-name')
    else:cfg.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    if not (dest/'evaluated-flow.json').exists():
        (dest/'evaluated-flow.json').write_text(json.dumps(original,ensure_ascii=False,indent=2),encoding='utf-8')
    if not (dest/'dataset-used.json').exists():
        (dest/'dataset-used.json').write_bytes((ROOT/'dataset.json').read_bytes())
    for test in tests:
        path=dest/(test['id']+'.json')
        if path.exists():print(test['id'],'already recorded',flush=True);continue
        start=time.perf_counter();result={'id':test['id'],'question':test['question'], 'started_utc':datetime.now(timezone.utc).isoformat(),
            'status':'error','answer':'','context':'','retrieved_chunks':[], 'node_seconds':{}, 'errors':[],
            'dense_candidates':[], 'lexical_candidates':[]}
        try:
            job=api.call('/build/'+args.flow_id+'/flow?event_delivery=streaming&log_builds=false',
                {'data':runflow,'inputs':{'components':['ChatInput-z2rit'],'input_value':test['question'],
                 'type':'chat','session':args.run_name+'-'+test['id']}},'POST',timeout=60)
            result['job_id']=job['job_id']
            req=Request(BASE+'/build/'+job['job_id']+'/events',headers={'Authorization':'Bearer '+api.token})
            completed=False
            with urlopen(req,timeout=180) as response:
                for raw in response:
                    line=raw.decode('utf-8').strip()
                    if not line:continue
                    if line.startswith('data:'):line=line[5:].strip()
                    event=json.loads(line); kind=event.get('event');data=event.get('data',{})
                    if kind=='end_vertex':
                        build=data['build_data'];nid=build['id'];payload=build.get('data',{})
                        result['node_seconds'][nid]=payload.get('timedelta')
                        if not build.get('valid'):result['errors'].append({'node':nid,'message':str(payload)[:2000]})
                        if nid=='Knowledge-Y8gm2':
                            result['dense_candidates']=payload.get('outputs',{}).get('retrieve_data',{}).get('message',[])
                            if result['dense_candidates'] and result['dense_candidates'][0].get('retrieval_trace'):
                                rows=result['dense_candidates']
                                result['retrieval_trace']=rows[0].pop('retrieval_trace')
                                for row in rows[1:]:row.pop('retrieval_trace',None)
                                result['query_plan']=result['retrieval_trace']['plan']
                                result['dense_candidates']=[r for trace in result['retrieval_trace']['queries'] for r in trace['dense_candidates']]
                                result['lexical_candidates']=[r for trace in result['retrieval_trace']['queries'] for r in trace['lexical_candidates']]
                                if args.retrieval_node==nid:result['retrieved_chunks']=rows
                            elif args.retrieval_node==nid:result['retrieved_chunks']=result['dense_candidates']
                        if nid=='TextbookBM25-SysArch':
                            result['lexical_candidates']=payload.get('outputs',{}).get('lexical_candidates',{}).get('message',[])
                        if nid=='TextbookRRF-SysArch' and args.retrieval_node==nid:
                            result['retrieved_chunks']=payload.get('outputs',{}).get('fused_candidates',{}).get('message',[])
                        if nid=='TextbookReranker-SysArch' and args.retrieval_node==nid:
                            rows=payload.get('outputs',{}).get('reranked_candidates',{}).get('message',[])
                            if rows and rows[0].get('rerank_trace'):
                                result['rerank_trace']=rows[0]['rerank_trace']
                            result['retrieved_chunks']=[{k:v for k,v in r.items() if k!='rerank_trace'} for r in rows]
                        if nid=='parser-h3mx9':result['context']=text_of(payload.get('artifacts',{}).get('parsed_text'))
                        if nid=='LanguageModelComponent-BpTTF':
                            result['raw_answer']=text_of(payload.get('artifacts',{}).get('text_output')) or text_of(payload.get('results',{}).get('text_output'))
                        if nid=='FinalAnswerCleaner-SysArch':result['cleaned_answer']=text_of(payload.get('artifacts',{}).get('cleaned_message'))
                        if nid=='ChatOutput-QRg8s':result['answer']=text_of(payload.get('results',{}).get('message')) or text_of(payload.get('artifacts'))
                    elif kind=='error':result['errors'].append(str(data)[:2000])
                    elif kind=='end':completed=True;result['server_seconds']=data.get('build_duration')
            if completed and result['answer'] and not result['errors']:result['status']='ok'
            elif not result['errors']:result['errors'].append('Missing terminal answer or completion event')
        except Exception as exc:result['errors'].append(str(exc)[:2000])
        result['elapsed_seconds']=round(time.perf_counter()-start,3)
        # Store actual outputs and context, not request headers, tokens, or component parameter dumps.
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(test['id'],result['status'],result['elapsed_seconds'],'sec',len(result['answer']),'chars',flush=True)
    after=api.call('/flows/'+args.flow_id)['data']
    unchanged=hashlib.sha256(json.dumps(after,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==fingerprint
    (dest/'run-summary.json').write_text(json.dumps({'finished_utc':datetime.now(timezone.utc).isoformat(),
        'flow_unchanged':unchanged,'flow_logic_unchanged':flow_logic_fingerprint(after)==logic_fingerprint,
        'results':[json.loads((dest/(t['id']+'.json')).read_text(encoding='utf-8'))['status'] for t in tests]},indent=2),encoding='utf-8')
    print('Finished; flow logic unchanged:',flow_logic_fingerprint(after)==logic_fingerprint,flush=True)

if __name__=='__main__':main()
