"""Audit real final runs, original sources and protected live flows."""
import json, re
from pathlib import Path
from datetime import datetime,timezone
from langflow_api import LangflowAPI
from hybrid_retrieval import load_snapshot
from run_rag_evaluation import flow_logic_fingerprint
from setup_complete_flow import ROOT

setup=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
index=load_snapshot(setup['snapshot_path'],setup['snapshot_sha256'])
dest=Path(r'F:\daily\output\sysarch-rag-evaluation\complete-rag-final-20261009')
summary=[]
for qid in ('Q02','Q11','Q17'):
    r=json.loads((dest/(qid+'.json')).read_text(encoding='utf-8'))
    assert r['status']=='ok' and not r['errors']
    trace=r['rerank_trace']
    assert trace['route']=='reranked' and trace['network_used'] is False
    assert trace['candidate_count']<=20 and len(r['retrieved_chunks'])<=5
    assert not trace['missing_queries']
    index.validate_candidates(r['retrieved_chunks'])
    assert [row['rag_rank'] for row in r['retrieved_chunks']]==list(range(1,len(r['retrieved_chunks'])+1))
    assert all(row['content'] in r['context'] for row in r['retrieved_chunks'])
    answer=r['cleaned_answer']
    assert '<think>' not in answer
    assert all(1<=int(rank)<=len(r['retrieved_chunks']) for rank in re.findall(r'\[片段(\d+)',answer))
    if qid=='Q02':assert r['query_plan']['planner_called'] is False
    if qid=='Q11':assert r['query_plan']['route']=='split' and len(r['query_plan']['queries'])==2
    if qid=='Q17':
        assert {q['chapter'] for q in r['query_plan']['queries']}=={9,17}
        assert any('第9章' in row['chapter'] for row in r['retrieved_chunks'])
        assert any('第17章' in row['chapter'] for row in r['retrieved_chunks'])
    summary.append({'id':qid,'question':r['question'],'route':r['query_plan']['route'],
        'reason':r['query_plan']['reason'],'candidate_count':trace['candidate_count'],
        'final_count':len(r['retrieved_chunks']),'missing_queries':trace['missing_queries'],
        'elapsed_seconds':r['elapsed_seconds'],'source_preserved':True})
api=LangflowAPI()
protected={fid:flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==old for fid,old in setup['protected_before'].items()}
assert all(protected.values())
current=api.call('/flows/'+setup['flow_id'])
evaluated=json.loads((dest/'evaluated-flow.json').read_text(encoding='utf-8'))
assert flow_logic_fingerprint(current['data'])==flow_logic_fingerprint(evaluated.get('data',evaluated))
kb=api.call('/knowledge_bases/SysArchTutorRAGv3/chunks?page=1&limit=1')
report={'verified_utc':datetime.now(timezone.utc).isoformat(),'flow_id':setup['flow_id'],
        'protected_unchanged':protected,'flow_matches_final_test':True,'kb_total':kb['total'],
        'tests':summary,'scope':'3题路径与来源校验，不代表完整准确率或整体效果提升'}
(ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
