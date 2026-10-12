"""Refresh only new experiment components during development."""
import json
from setup_complete_flow import ROOT, PROTECTED
from complete_components import COMPLETE_RETRIEVER_CODE, COMPLETE_RERANK_CODE, COMPLETE_PLANNER_CODE
from setup_hybrid_flow import component
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint

api=LangflowAPI()
setup=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
flow=api.call('/flows/'+setup['flow_id'])
for i,n in enumerate(flow['data']['nodes']):
    if n['id'] not in ('Knowledge-Y8gm2','TextbookReranker-SysArch','TextbookQueryPlanner-SysArch'):continue
    code={'Knowledge-Y8gm2':COMPLETE_RETRIEVER_CODE,'TextbookReranker-SysArch':COMPLETE_RERANK_CODE,'TextbookQueryPlanner-SysArch':COMPLETE_PLANNER_CODE}[n['id']]
    keys=[] if n['id']=='TextbookQueryPlanner-SysArch' else ['snapshot_path','snapshot_sha256','final_k']+(['knowledge_base','top_k','rrf_constant'] if n['id']=='Knowledge-Y8gm2' else [])
    values={k:n['data']['node']['template'][k]['value'] for k in keys}
    replacement=component(api,code,n['id'],n['position'],values)
    assert replacement['data']['type']==n['data']['type']
    flow['data']['nodes'][i]=replacement
api.call('/flows/'+setup['flow_id'],{'data':flow['data']},'PATCH')
saved=api.call('/flows/'+setup['flow_id'])
(ROOT/'experiment-flow.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==setup['protected_before'][fid] for fid in PROTECTED)
print('Complete experiment refreshed; existing flows unchanged')
