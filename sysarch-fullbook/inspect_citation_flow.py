from pathlib import Path
from langflow_api import LangflowAPI
from printed_page_mapping import ROOT
from core import save_json_atomic

api=LangflowAPI()
for fid in ['2e38f267-52d8-484f-bc4a-81ad7a2e3436','7b965a0c-d610-42b0-a986-8557aadb207a']:
    flow=api.call('/flows/'+fid)
    save_json_atomic(ROOT/'backups'/(flow['name']+'-before-dual-pages.json'),flow)
    print(flow['name'],flow['id'])
    for node in flow['data']['nodes']:
        t=node['data']['node']['template']
        if node['id']=='parser-h3mx9':
            (ROOT/'parser-before.py').write_text(t['code']['value'],encoding='utf-8')
        if node['id']=='Prompt Template-fzcHC':
            (ROOT/'prompt-before.txt').write_text(t['template']['value'],encoding='utf-8')
        for key in ['knowledge_base','batch_file','pattern']:
            if key in t: print(node['id'],key,t[key].get('value'))
