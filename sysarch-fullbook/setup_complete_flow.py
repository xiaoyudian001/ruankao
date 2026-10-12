"""Create complete experiment only; persist ID before follow-up verification."""
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from setup_hybrid_flow import component, edge
from run_rag_evaluation import flow_logic_fingerprint
from complete_components import COMPLETE_RETRIEVER_CODE, COMPLETE_RERANK_CODE, COMPLETE_PLANNER_CODE

ROOT=Path(r'F:\daily\output\sysarch-complete-rag')
SOURCE='730d9bd5-e084-4b32-814e-edea8d404c4b'
PROTECTED=['2e38f267-52d8-484f-bc4a-81ad7a2e3436','da6fd96e-f7fc-47fc-ae4f-e320febf0a6f',SOURCE,'82dfc558-642f-4eb0-8037-05b2f153e7bd']

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    api=LangflowAPI()
    if (ROOT/'setup.json').exists():
        saved=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
        print(json.dumps({'existing_flow_id':saved['flow_id']}));return
    before={fid:api.call('/flows/'+fid) for fid in PROTECTED}
    for fid,flow in before.items():
        (ROOT/(fid+'-before.json')).write_text(json.dumps(flow,ensure_ascii=False,indent=2),encoding='utf-8')
    source=before[SOURCE]
    data=copy.deepcopy(source['data'])
    shared=json.loads(Path(r'F:\daily\output\sysarch-hybrid-retrieval\setup.json').read_text(encoding='utf-8'))
    shared={k:shared[k] for k in ('snapshot_path','snapshot_sha256')}
    retrieve=component(api,COMPLETE_RETRIEVER_CODE,'Knowledge-Y8gm2',{'x':1000,'y':40},
        {**shared,'knowledge_base':'SysArchTutorRAGv3','top_k':20,'final_k':5,'rrf_constant':60})
    rerank=component(api,COMPLETE_RERANK_CODE,'TextbookReranker-SysArch',{'x':1550,'y':40},{**shared,'final_k':5})
    planner=component(api,COMPLETE_PLANNER_CODE,'TextbookQueryPlanner-SysArch',{'x':500,'y':40},{})
    data['nodes']=[retrieve if n['id']=='Knowledge-Y8gm2' else planner if n['id']==planner['id'] else n for n in data['nodes']]+[rerank]
    # Replace every downstream retrieval reference, including citation binding.
    outgoing=[e for e in data['edges'] if e['source']=='Knowledge-Y8gm2']
    assert {e['target'] for e in outgoing}=={'parser-h3mx9','FinalAnswerCleaner-SysArch'}
    data['edges']=[e for e in data['edges'] if e['source']!='Knowledge-Y8gm2']
    for e in outgoing:
        th=e['data']['targetHandle']
        data['edges'].append(edge(rerank['id'],rerank['data']['type'],'reranked_candidates',
            rerank['data']['node']['outputs'][0]['types'],e['target'],th['fieldName'],th['inputTypes'],th['type']))
    data['edges'] += [
        edge(retrieve['id'],retrieve['data']['type'],'retrieve_data',retrieve['data']['node']['outputs'][0]['types'],
            rerank['id'],'candidates',['DataFrame','Table'],'other'),
        edge('ChatInput-z2rit','ChatInput','message',['Message'],rerank['id'],'question',['Message'],'str')]
    positions={'parser-h3mx9':(2100,40),'Prompt Template-fzcHC':(2100,470),
        'LanguageModelComponent-BpTTF':(1550,650),'FinalAnswerCleaner-SysArch':(2100,900),'ChatOutput-QRg8s':(1550,1100)}
    for n in data['nodes']:
        if n['id'] in positions:
            x,y=positions[n['id']];n['position']={'x':x,'y':y}
    data['viewport']={'x':10,'y':10,'zoom':.35}
    flow=api.call('/flows/',{'name':'教材检索与备考问答 · 完整检索实验',
        'description':'按需拆分→逐问题语义/BM25/RRF→合并20→本地MiniLM重排与子问题覆盖→5片→MiniMax回答。',
        'folder_id':source['folder_id'],'data':data},'POST')
    setup={'flow_id':flow['id'],'flow_name':flow['name'],**shared,'candidate_k':20,'final_k':5,
        'protected_ids':PROTECTED,'website_mode':'complete','protected_before':{fid:flow_logic_fingerprint(f['data']) for fid,f in before.items()}}
    (ROOT/'setup.json').write_text(json.dumps(setup,ensure_ascii=False,indent=2),encoding='utf-8')
    saved=api.call('/flows/'+flow['id'])
    assert flow_logic_fingerprint(saved['data'])==flow_logic_fingerprint(data)
    assert all(flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==setup['protected_before'][fid] for fid in PROTECTED)
    (ROOT/'experiment-flow.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'flow_id':flow['id'],'nodes':len(data['nodes']),'connections':len(data['edges']),'protected_unchanged':True},ensure_ascii=False))

if __name__=='__main__':main()
