"""Add retrieval snapshots to the four web answer flows, with rollback on partial failure."""
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from setup_hybrid_flow import component
from citation_validation_component import cleaner_code
from run_rag_evaluation import flow_logic_fingerprint

ROOT = Path(r'F:\daily\output\sysarch-citation-viewer')
FLOWS = {'default':'2e38f267-52d8-484f-bc4a-81ad7a2e3436',
         'complete':'ce82698e-54b8-4360-8a11-6f6c4f43f5ff',
         'conversation_default':'94e0161b-b811-46e4-807a-c5a4c5f05806',
         'conversation_complete':'f237233c-36bb-4d47-9f3b-fc456b911edb'}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    api = LangflowAPI()
    originals = {}; candidates = {}
    for label, fid in FLOWS.items():
        saved = api.call('/flows/'+fid)
        original = saved['data']; originals[label] = original
        backup = ROOT/(label+'-before.json')
        if not backup.exists():
            backup.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
        data = copy.deepcopy(original)
        node = next(n for n in data['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
        code = cleaner_code(node['data']['node']['template']['code']['value'])
        compiled = component(api, code, node['id'], node['position'], {})
        node['data']['node'] = compiled['data']['node']
        node['data']['type'] = compiled['data']['type']
        restored = copy.deepcopy(data)
        next(n for n in restored['nodes'] if n['id']==node['id'])['data'] = copy.deepcopy(
            next(n for n in original['nodes'] if n['id']==node['id'])['data'])
        assert restored == original, 'Unexpected changes outside final cleaner'
        candidates[label] = data
    applied = []
    try:
        for label, fid in FLOWS.items():
            assert flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==flow_logic_fingerprint(originals[label])
            api.call('/flows/'+fid, {'data':candidates[label]}, 'PATCH')
            applied.append(label)
            assert api.call('/flows/'+fid)['data'] == candidates[label]
    except Exception:
        for label in applied:
            api.call('/flows/'+FLOWS[label], {'data':originals[label]}, 'PATCH')
        raise
    manifest = {'flows':FLOWS, 'changes':['final cleaner session_metadata.textbook_refs'],
                'retrieval_model_prompt_edges_unchanged':True}
    (ROOT/'activation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':
    main()
