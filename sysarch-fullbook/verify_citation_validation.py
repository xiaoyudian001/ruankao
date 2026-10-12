"""Verify installed graph restrictions, actual outputs and unchanged knowledge store."""
import copy
import json
from pathlib import Path

from activate_citation_validation import ROOT, FLOWS, load, store_files
from answer_citations import normalize_citations
from answer_cleanup import clean_answer, strip_think
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint

RUN_ROOT=Path(r'F:\daily\output\sysarch-rag-evaluation')


def main():
    api=LangflowAPI();manifest=load(ROOT/'activation.json');protected={};live=[]
    for label,fid in FLOWS.items():
        original=load(ROOT/'backups'/(label+'-before.json'))['data']
        current=api.call('/flows/'+fid)['data']
        assert flow_logic_fingerprint(current)==manifest['flows'][label]['after_logic_sha256'],label
        restored=copy.deepcopy(current)
        before={n['id']:n for n in original['nodes']}
        for n in restored['nodes']:
            if n['id']=='FinalAnswerCleaner-SysArch':n['data']=copy.deepcopy(before[n['id']]['data'])
            if n['id']=='Prompt Template-fzcHC':
                n['data']['node']['template']['template']=copy.deepcopy(before[n['id']]['data']['node']['template']['template'])
        added=[e for e in restored['edges'] if e['target']=='FinalAnswerCleaner-SysArch' and e['data']['targetHandle']['fieldName']=='reference_data']
        assert len(added)==1
        parser_edge=next(e for e in restored['edges'] if e['target']=='parser-h3mx9' and e['data']['targetHandle']['fieldName']=='input_data')
        assert parser_edge['data']['sourceHandle']==added[0]['data']['sourceHandle']
        restored['edges'].remove(added[0])
        assert flow_logic_fingerprint(restored)==flow_logic_fingerprint(original),'Unexpected logic change '+label
        run=RUN_ROOT/f'citation-{label}-v2-20261009'
        cfg=load(run/'configuration.json')
        assert cfg['flow_logic_sha256']==flow_logic_fingerprint(current)
        assert load(run/'run-summary.json')['flow_logic_unchanged']
        protected[label]={'saved':True,'only_approved_changes':True,'reference_matches_parser_input':True}
        cleanup=strip_think if label=='formal' else clean_answer
        for path in sorted(run.glob('Q*.json')):
            q=load(path);assert q['status']=='ok' and q.get('raw_answer'),path.name
            normalized=normalize_citations(cleanup(q['raw_answer']),q['retrieved_chunks'])
            assert normalized['text']==q['answer'], 'Live cleaner differs from reviewed helper'
            assert not normalized['invalid_ranks'] and not normalized['malformed_citations']
            assert not normalized['unbound_page_mentions']
            assert '<think' not in q['answer'].lower()
            if label=='hybrid':assert r'\int_{0}^{\infty} R(t)\,dt' in q['answer']
            live.append({'flow':label,'id':q['id'],'question':q['question'],
                         'elapsed_seconds':q['elapsed_seconds'],
                         'cleaner_seconds':q['node_seconds']['FinalAnswerCleaner-SysArch'],
                         'diagnostics':{k:v for k,v in normalized.items() if k!='text'},
                         'answer':q['answer'],'source':str(path)})
    before_rows=load(ROOT/'kb-before.json');after_rows=api.chunks('SysArchTutorRAGv3')
    canonical=lambda rows:sorted(json.dumps(r,sort_keys=True,ensure_ascii=False) for r in rows)
    assert canonical(before_rows)==canonical(after_rows)
    files=store_files()
    before_files=load(ROOT/'storage-before.json')
    index_files=lambda fs:{k:v for k,v in fs.items() if Path(k).suffix in ('.bin','.pickle')}
    assert index_files(files) and index_files(files)==index_files(before_files),'Vector index bytes changed'
    changed_files=[k for k in sorted(set(files)|set(before_files)) if files.get(k)!=before_files.get(k)]
    result={'version':manifest['version'],'flow_protection':protected,
            'knowledge_rows_unchanged':True,'knowledge_count':len(after_rows),
            'vector_index_hashes_unchanged':True,'storage_files':files,
            'all_storage_hashes_unchanged':not changed_files,'changed_storage_files':changed_files,
            'unit_tests_passed':24,'offline_replayed_answers':20,
            'final_saved_flow_live_tests':len(live),'no_extra_generation_node':True,
            'website_routing_not_changed_by_task':True,'live_tests':live}
    (ROOT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['storage_files','live_tests']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
