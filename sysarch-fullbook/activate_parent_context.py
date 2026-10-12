"""Insert the parent node before both context parsing and citation snapshotting."""
import copy
import json
from pathlib import Path

from activate_source_references import FLOWS
from core import save_json_atomic
from langflow_api import LangflowAPI
from parent_context_component import PARENT_CODE
from setup_hybrid_flow import component, edge, digest

ROOT=Path(r'F:\daily\output\sysarch-parent-context')
NODE='TextbookParentContext-SysArch'
RULE='''\n父级上下文说明：每个片段标明直接命中或相邻上下文，以及所属标题。相邻片段用于补齐被截断的定义、条件和列表；只引用直接支持结论的编号，不因相邻关系推断结论。引用的页码范围由输出程序依据每个片段自身元数据填写。\n'''


def prepare(api,original,settings):
    data=copy.deepcopy(original)
    assert not any(n['id']==NODE for n in data['nodes']), 'Parent node already exists'
    parser=next(n for n in data['nodes'] if n['id']=='parser-h3mx9')
    cleaner=next(n for n in data['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
    assert 'textbook_refs' in cleaner['data']['node']['template']['code']['value'], 'Snapshot cleaner required'
    evidence=[e for e in data['edges'] if
              (e['target']==parser['id'] and e['data']['targetHandle']['fieldName']=='input_data') or
              (e['target']==cleaner['id'] and e['data']['targetHandle']['fieldName']=='reference_data')]
    assert len(evidence)==2 and evidence[0]['data']['sourceHandle']==evidence[1]['data']['sourceHandle']
    source=evidence[0]['data']['sourceHandle']
    node=component(api,PARENT_CODE,NODE,{'x':parser['position']['x']+420,'y':parser['position']['y']-180},
                   {'index_path':settings['index_path'],'index_sha256':settings['index_sha256'],
                    'enabled':True,'max_chars':10000,'max_sources':10})
    data['nodes'].append(node)
    data['edges']=[e for e in data['edges'] if e not in evidence]
    data['edges'].append(edge(source['id'],source['dataType'],source['name'],source['output_types'],
                              NODE,'hits',['DataFrame','Table'],'other'))
    for target,field in [(parser['id'],'input_data'),(cleaner['id'],'reference_data')]:
        data['edges'].append(edge(NODE,node['data']['type'],'expanded_context',['DataFrame'],
                                  target,field,['DataFrame','Table','Data','JSON'],'other'))
    parser['data']['node']['template']['pattern']['value']='[片段{rag_rank}]\n{source_hint}\n{context_hint}\n{content}'
    prompt=next(n for n in data['nodes'] if n['id']=='Prompt Template-fzcHC')['data']['node']['template']['template']
    assert '教材片段' in prompt['value'] and RULE not in prompt['value']
    prompt['value']=RULE+prompt['value']
    # Permit exactly the new node, its three wires, and the two context presentation fields.
    restored=copy.deepcopy(data)
    restored['nodes']=[n for n in restored['nodes'] if n['id']!=NODE]
    restored['edges']=copy.deepcopy(original['edges'])
    for nid,key in [('parser-h3mx9','pattern'),('Prompt Template-fzcHC','template')]:
        old=next(n for n in original['nodes'] if n['id']==nid)['data']['node']['template'][key]
        next(n for n in restored['nodes'] if n['id']==nid)['data']['node']['template'][key]=copy.deepcopy(old)
    assert restored==original,'Unexpected change outside parent integration'
    return data


def main():
    api=LangflowAPI();settings=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
    originals={};updated={};backups=ROOT/'flow-backups';backups.mkdir(exist_ok=True)
    for label,fid in FLOWS.items():
        saved=api.call('/flows/'+fid);originals[label]=saved['data']
        backup=backups/(label+'-before.json');assert not backup.exists(),'Backup already exists; inspect previous activation'
        save_json_atomic(backup,saved)
        updated[label]=prepare(api,saved['data'],settings)
    applied=[]
    try:
        for label,fid in FLOWS.items():
            assert api.call('/flows/'+fid)['data']==originals[label],'Concurrent flow edit'
            api.call('/flows/'+fid,{'data':updated[label]},'PATCH');applied.append(label)
            assert api.call('/flows/'+fid)['data']==updated[label]
    except Exception:
        for label in reversed(applied):
            # Do not overwrite a new edit made after this script's patch.
            if api.call('/flows/'+FLOWS[label])['data']==updated[label]:
                api.call('/flows/'+FLOWS[label],{'data':originals[label]},'PATCH')
        raise
    report={'flows':FLOWS,'node':NODE,'index':settings,
            'changes':['parent expansion node','shared parser and citation input','context role labels'],
            'retrieval_and_model_settings_unchanged':True,
            'hashes':{label:{'before':digest(originals[label]),'after':digest(updated[label])} for label in FLOWS}}
    save_json_atomic(ROOT/'activation.json',report);print(json.dumps({'activated_flows':list(FLOWS),'node':NODE}))


if __name__=='__main__':main()
