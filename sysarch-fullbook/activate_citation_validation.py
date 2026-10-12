"""Activate only output citation formatting; retain immutable rollback snapshots."""
import copy
import argparse
import hashlib
import json
import re
from pathlib import Path

from citation_validation_component import cleaner_code
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint
from setup_hybrid_flow import component, edge

ROOT = Path(r'F:\daily\output\sysarch-citation-validation')
FLOWS = {'formal':'2e38f267-52d8-484f-bc4a-81ad7a2e3436',
         'hybrid':'da6fd96e-f7fc-47fc-ae4f-e320febf0a6f',
         'subquery':'730d9bd5-e084-4b32-814e-edea8d404c4b'}
KB_PATH = Path(r'C:\Users\78052\.langflow\knowledge_bases\langflow\SysArchTutorRAGv3')
RULE = ('- 引用只输出实际支持结论的片段编号，例如“[片段1][片段3]”。'
        '不要自行填写教材页码、PDF页码、章节或来源列表中的页码；输出程序会根据本次检索元数据填写完整出处。'
        '不得引用未提供的编号，不要为缺乏依据的结论补引用。来源范围表示整个检索片段，不代表精确定位到其中某句话。')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def store_files():
    files = {}
    for p in sorted(KB_PATH.rglob('*')):
        if p.is_file():
            h = hashlib.sha256()
            with p.open('rb') as f:
                for part in iter(lambda:f.read(1024*1024), b''):
                    h.update(part)
            files[str(p.relative_to(KB_PATH))] = h.hexdigest()
    assert files, 'Knowledge store not found'
    return files


def prepare(api, original):
    data = copy.deepcopy(original)
    nodes = {n['id']:n for n in data['nodes']}
    old = nodes['FinalAnswerCleaner-SysArch']
    code = cleaner_code(old['data']['node']['template']['code']['value'])
    new = component(api, code, old['id'], old['position'], {})
    # Preserve canvas/component identity; only replace the cleaner definition.
    old['data']['node'] = new['data']['node']
    old['data']['type'] = new['data']['type']
    prompt = nodes['Prompt Template-fzcHC']['data']['node']['template']['template']
    prompt['value'], count = re.subn(r'- 引用须.*?(?=\n\n教材片段)', RULE, prompt['value'], flags=re.S)
    assert count == 1, 'Expected one existing citation instruction'
    upstream = [e for e in data['edges'] if e['target']=='parser-h3mx9' and e['data']['targetHandle']['fieldName']=='input_data']
    assert len(upstream)==1
    source = upstream[0]['data']['sourceHandle']
    added = edge(source['id'],source['dataType'],source['name'],source['output_types'],
                 old['id'],'reference_data',['DataFrame','Table','Data','JSON'],'other')
    data['edges'].append(added)
    restored = copy.deepcopy(data)
    before = {n['id']:n for n in original['nodes']}
    for n in restored['nodes']:
        if n['id']==old['id']:n['data']=copy.deepcopy(before[n['id']]['data'])
        if n['id']=='Prompt Template-fzcHC':
            n['data']['node']['template']['template']=copy.deepcopy(before[n['id']]['data']['node']['template']['template'])
    restored['edges'].remove(added)
    assert restored==original, 'Unexpected change outside cleaner, prompt and evidence edge'
    return data


def refresh(api, manifest):
    """Update cleaner helpers after a regression fix; keep prompt and edges fixed."""
    originals={};updated={}
    for label,fid in FLOWS.items():
        current=api.call('/flows/'+fid)['data']
        assert flow_logic_fingerprint(current)==manifest['flows'][label]['after_logic_sha256'], 'Concurrent logic edit'
        original_cleaner=next(n for n in load(ROOT/'backups'/(label+'-before.json'))['data']['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
        code=cleaner_code(original_cleaner['data']['node']['template']['code']['value'])
        data=copy.deepcopy(current)
        node=next(n for n in data['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
        compiled=component(api,code,node['id'],node['position'],{})
        node['data']['node']=compiled['data']['node']
        node['data']['type']=compiled['data']['type']
        originals[label]=current;updated[label]=data
        restored=copy.deepcopy(data)
        next(n for n in restored['nodes'] if n['id']==node['id'])['data']=copy.deepcopy(next(n for n in current['nodes'] if n['id']==node['id'])['data'])
        assert restored==current
    applied=[]
    try:
        for label,fid in FLOWS.items():
            assert flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==flow_logic_fingerprint(originals[label])
            api.call('/flows/'+fid,{'data':updated[label]},'PATCH');applied.append(label)
            saved=api.call('/flows/'+fid)
            assert saved['data']==updated[label]
            (ROOT/'backups'/(label+'-after.json')).write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
            manifest['flows'][label]['after_logic_sha256']=flow_logic_fingerprint(saved['data'])
    except Exception:
        for label in applied:api.call('/flows/'+FLOWS[label],{'data':originals[label]},'PATCH')
        raise
    manifest['version']='source-bound-output-citations-v2'
    (ROOT/'activation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Cleaner helpers updated; prompts, retrieval, models and edges unchanged.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-cleaners',action='store_true');args=parser.parse_args()
    api = LangflowAPI()
    manifest_path = ROOT/'activation.json'
    if manifest_path.exists():
        manifest=load(manifest_path)
        if args.refresh_cleaners:
            refresh(api,manifest);return
        for label, fid in FLOWS.items():
            assert flow_logic_fingerprint(api.call('/flows/'+fid)['data']) == manifest['flows'][label]['after_logic_sha256']
        print('Existing output citation validation still active.');return
    if not (ROOT/'kb-before.json').exists():
        (ROOT/'kb-before.json').write_text(json.dumps(api.chunks('SysArchTutorRAGv3'),ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/'storage-before.json').write_text(json.dumps(store_files(),indent=2),encoding='utf-8')
    originals = {}; candidates = {}
    for label, fid in FLOWS.items():
        saved = api.call('/flows/'+fid)
        before=load(ROOT/'backups'/(label+'-before.json'))
        assert flow_logic_fingerprint(before['data']) == flow_logic_fingerprint(saved['data']), 'Concurrent logic edit'
        originals[label]=saved['data']
        candidates[label]=prepare(api,saved['data'])
        (ROOT/(label+'-candidate.json')).write_text(json.dumps(candidates[label],ensure_ascii=False,indent=2),encoding='utf-8')
    applied = []
    try:
        for label, fid in FLOWS.items():
            assert flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==flow_logic_fingerprint(originals[label])
            api.call('/flows/'+fid,{'data':candidates[label]},'PATCH')
            applied.append(label)
            saved=api.call('/flows/'+fid)
            assert saved['data']==candidates[label]
            (ROOT/'backups'/(label+'-after.json')).write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        for label in applied:
            api.call('/flows/'+FLOWS[label],{'data':originals[label]},'PATCH')
        raise
    manifest={'version':'source-bound-output-citations-v1','flows':{
        label:{'flow_id':fid,'before_logic_sha256':flow_logic_fingerprint(originals[label]),
               'after_logic_sha256':flow_logic_fingerprint(candidates[label]),
               'changes':['FinalAnswerCleaner component','citation instruction','reference_data evidence edge'],
               'retrieval_and_model_unchanged':True} for label,fid in FLOWS.items()},
        'no_additional_model_request':True,'website_target_not_changed':True}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
