import ast
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from core import save_json_atomic
from parse_book import ROOT

api=LangflowAPI()
fid='2e38f267-52d8-484f-bc4a-81ad7a2e3436'
flow=api.call('/flows/'+fid)
original_data=copy.deepcopy(flow['data'])
data=flow['data']
nodes={n['id']:n for n in data['nodes']}
parser=nodes['parser-h3mx9']['data']['node']['template']
code=parser['code']['value']
helper=Path(__file__).with_name('citation_format.py').read_text(encoding='utf-8')
if '\ndef source_hint(' not in code:
    code=code.replace('class _DefaultDict',helper+'\n\nclass _DefaultDict',1)
    old='row_values["rag_rank"] = rank'
    assert code.count(old)==1
    code=code.replace(old,old+'\n                row_values["source_hint"] = source_hint(row_values)')
    ast.parse(code)
    parser['code']['value']=code
parser['pattern']['value']='[片段{rag_rank}]\n{source_hint}\n{content}'
prompt=nodes['Prompt Template-fzcHC']['data']['node']['template']['template']
rule=('- 引用同时给出实际使用的片段编号与对应来源中的原PDF页码，例如“[片段1，原PDF第25～26页]”。'
      '原PDF页码是文件物理页，不是书上印刷页码；不得缩小或扩大片段提供的页码范围。'
      '来源未记录页码时，只引用片段编号。\n')
if rule not in prompt['value']:
    prompt['value']=prompt['value'].replace('教材片段：',rule+'\n教材片段：')
assert api.call('/flows/'+fid)['data']==original_data, 'Concurrent edit detected'
updated=api.call('/flows/'+fid,{'data':data},'PATCH')
save_json_atomic(ROOT/'qa_with_page_citations.json',updated)
print('Citation formatter saved. Existing QA remains on',nodes['Knowledge-Y8gm2']['data']['node']['template']['knowledge_base']['value'])
