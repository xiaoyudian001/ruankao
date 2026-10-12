"""Create a new independent experiment without changing either existing flow."""
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from setup_hybrid_flow import component, edge, digest
from subquery_components import PLANNER_CODE, RETRIEVER_CODE

ROOT=Path(r'F:\daily\output\sysarch-subquery-retrieval')
SOURCE='da6fd96e-f7fc-47fc-ae4f-e320febf0a6f'
FORMAL='2e38f267-52d8-484f-bc4a-81ad7a2e3436'

def main():
    api=LangflowAPI()
    if (ROOT/'setup.json').exists():
        saved=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
        print(json.dumps({'existing_flow_id':saved['flow_id']},ensure_ascii=False));return
    source=api.call('/flows/'+SOURCE)
    assert source['data']==json.loads((ROOT/'hybrid-before.json').read_text(encoding='utf-8'))['data']
    index=json.loads(Path(r'F:\daily\output\sysarch-hybrid-retrieval\setup.json').read_text(encoding='utf-8'))
    shared={k:index[k] for k in ('snapshot_path','snapshot_sha256')}
    planner=component(api,PLANNER_CODE,'TextbookQueryPlanner-SysArch',{'x':530,'y':40},{})
    retriever=component(api,RETRIEVER_CODE,'Knowledge-Y8gm2',{'x':1080,'y':40},
                        {**shared,'knowledge_base':'SysArchTutorRAGv3','top_k':20,'final_k':5,'rrf_constant':60})
    data=copy.deepcopy(source['data'])
    removed={'Knowledge-Y8gm2','TextbookBM25-SysArch','TextbookRRF-SysArch'}
    data['nodes']=[n for n in data['nodes'] if n['id'] not in removed]
    model=copy.deepcopy(next(n for n in data['nodes'] if n['id']=='LanguageModelComponent-BpTTF'))
    model['id']='SubqueryPlannerModel-SysArch';model['data']['id']=model['id']
    model['position']={'x':30,'y':440}
    model['data']['selected_output']='model_output'
    model['data']['node']['display_name']='MiniMax 搜索计划模型'
    tmpl=model['data']['node']['template']
    for k,v in {'temperature':.1,'max_tokens':2048,'input_value':'','system_message':'','stream':False}.items():tmpl[k]['value']=v
    data['nodes'] += [model,planner,retriever]
    data['edges']=[e for e in data['edges'] if e['source'] not in removed and e['target'] not in removed]
    data['edges'] += [
      edge('ChatInput-z2rit','ChatInput','message',['Message'],planner['id'],'question',['Message'],'str'),
      edge(model['id'],model['data']['type'],'model_output',['LanguageModel'],planner['id'],'planner_model',['LanguageModel'],'other'),
      edge(planner['id'],planner['data']['type'],'query_plan',planner['data']['node']['outputs'][0]['types'],retriever['id'],'query_plan',['Data','JSON'],'other'),
      edge(retriever['id'],retriever['data']['type'],'retrieve_data',retriever['data']['node']['outputs'][0]['types'],'parser-h3mx9','input_data',['DataFrame','Table','Data','JSON'],'other'),
    ]
    pos={'ChatInput-z2rit':(30,40),'parser-h3mx9':(1620,40),'Prompt Template-fzcHC':(1620,480),
         'LanguageModelComponent-BpTTF':(1080,750),'FinalAnswerCleaner-SysArch':(1620,950),'ChatOutput-QRg8s':(1080,1200)}
    for n in data['nodes']:
        if n['id'] in pos:
            x,y=pos[n['id']];n['position']={'x':x,'y':y}
    data['viewport']={'x':10,'y':10,'zoom':.4}
    flow=api.call('/flows/',{'name':'教材检索与备考问答 · 问题拆分混合检索实验',
             'description':'简单问题直通；复杂问题2～3条受约束搜索计划→逐问题语义20/BM2520/RRF→最多5片证据。独立实验，网页未切换。',
             'folder_id':source['folder_id'],'data':data},'POST')
    saved=api.call('/flows/'+flow['id'])
    assert saved['data']==data
    for label,fid in [('hybrid',SOURCE),('formal',FORMAL)]:
        assert api.call('/flows/'+fid)['data']==json.loads((ROOT/(label+'-before.json')).read_text(encoding='utf-8'))['data']
    (ROOT/'experiment-flow.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    setup={'flow_id':flow['id'],'flow_name':flow['name'],'source_flow_id':SOURCE,'flow_sha256':digest(data),
           **shared,'final_k':5,'candidate_k':20,'planner_timeout_seconds':45,'max_subqueries':3,
           'query_concurrency':2,'planner_temperature':.1,'answer_temperature':.2,'website_switched':False}
    (ROOT/'setup.json').write_text(json.dumps(setup,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(setup,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
