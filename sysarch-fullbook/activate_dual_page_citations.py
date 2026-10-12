"""Patch only QA source formatter and its citation instruction through Langflow API."""
import ast
import copy
import json
from pathlib import Path
from core import save_json_atomic
from langflow_api import LangflowAPI
from printed_page_mapping import ROOT

FLOW_ID='2e38f267-52d8-484f-bc4a-81ad7a2e3436'

def patch_data(original):
    data=copy.deepcopy(original)
    nodes={n['id']:n for n in data['nodes']}
    parser=nodes['parser-h3mx9']['data']['node']['template']
    code=parser['code']['value']
    tree=ast.parse(code)
    old=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_hint')
    lines=code.splitlines(keepends=True)
    helper=Path(__file__).with_name('citation_format.py').read_text(encoding='utf-8')
    desired=ast.parse(helper).body[0]
    if ast.dump(old,include_attributes=False)!=ast.dump(desired,include_attributes=False):
        lines[old.lineno-1:old.end_lineno]=[helper+'\n']
        code=''.join(lines)
        ast.parse(code)
        parser['code']['value']=code
    assert parser['pattern']['value']=='[片段{rag_rank}]\n{source_hint}\n{content}'
    prompt=nodes['Prompt Template-fzcHC']['data']['node']['template']['template']
    old_rule=('- 引用同时给出实际使用的片段编号与对应来源中的原PDF页码，例如“[片段1，原PDF第25～26页]”。'
              '原PDF页码是文件物理页，不是书上印刷页码；不得缩小或扩大片段提供的页码范围。'
              '来源未记录页码时，只引用片段编号。')
    rule=('- 引用须给出实际使用的片段编号，并完整照抄该片段来源里的教材页码与PDF页码，'
          '例如“[片段1，教材第308页（PDF第323页）]”或“[片段2，教材第613～614页（PDF第628～629页）]”。'
          '教材页码是书页上印出的页码；PDF页码是文件从第1页开始的物理页序。'
          '来源只记录原PDF页码时，引用“[片段编号，原PDF第X页]”，不得自行减15或猜测教材页码。'
          '不得缩小或扩大片段提供的页码范围。来源未记录页码时，只引用片段编号。')
    if rule not in prompt['value']:
        assert prompt['value'].count(old_rule)==1, 'Citation instruction changed; review required'
        prompt['value']=prompt['value'].replace(old_rule,rule)
    return data

def activate():
    verification=json.loads((ROOT/'metadata-verification.json').read_text(encoding='utf-8'))
    assert verification['ids_text_and_vectors_unchanged'] and verification['chunks']==1675
    api=LangflowAPI();flow=api.call('/flows/'+FLOW_ID)
    original=copy.deepcopy(flow['data'])
    backup=ROOT/'backups'/(flow['name']+'-before-dual-pages.json')
    if not backup.exists(): save_json_atomic(backup,flow)
    updated=patch_data(original)
    assert api.call('/flows/'+FLOW_ID)['data']==original, 'Concurrent flow edit detected'
    api.call('/flows/'+FLOW_ID,{'data':updated},'PATCH')
    saved=api.call('/flows/'+FLOW_ID)
    assert saved['data']==updated
    nodes={n['id']:n for n in updated['nodes']}
    assert nodes['Knowledge-Y8gm2']['data']['node']['template']['knowledge_base']['value']=='SysArchTutorRAGv3'
    save_json_atomic(ROOT/'backups'/(flow['name']+'-after-dual-pages.json'),saved)
    save_json_atomic(ROOT/'flow-verification.json',{'flow_id':FLOW_ID,'name':flow['name'],
                      'citation_formatter_and_prompt_saved':True,'kb':'SysArchTutorRAGv3'})
    print('DUAL_PAGES_ACTIVE',flow['name'])

if __name__=='__main__': activate()
