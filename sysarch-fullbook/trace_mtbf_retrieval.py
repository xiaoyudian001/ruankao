import json
import math
from pathlib import Path
from urllib.request import Request,urlopen
from langflow_api import LangflowAPI
from core import save_json_atomic
from verify_qa import context_text

ROOT=Path(r'F:\daily\output\sysarch-rag-explanation')
QUESTION='解释一下什么是MTBF并指出在教材的哪一页'

api=LangflowAPI()
body={'input_request':{'input_value':QUESTION,'input_type':'chat','output_type':'any',
    'output_component':'Knowledge-Y8gm2','session_id':'explain-mtbf-retrieval',
    'tweaks':{'ChatInput-z2rit':{'should_store_message':False},
              'ChatOutput-QRg8s':{'should_store_message':False}}}}
raw=api.call('/run/session/2e38f267-52d8-484f-bc4a-81ad7a2e3436',body,'POST',timeout=90)
save_json_atomic(ROOT/'mtbf-retrieval.json',raw)
body['input_request']['output_component']='parser-h3mx9'
context_result=api.call('/run/session/2e38f267-52d8-484f-bc4a-81ad7a2e3436',body,'POST',timeout=90)
save_json_atomic(ROOT/'mtbf-context.json',context_result)
(ROOT/'mtbf-context.txt').write_text(context_text(context_result),encoding='utf-8')
backup=json.loads(Path(r'F:\daily\output\sysarch-page-citations\backups\SysArchTutorRAGv3-before-dual-pages-vectors.json').read_text(encoding='utf-8'))
vectors=backup['embeddings']
vector_info={'dimensions':len(vectors[0]),'stored_vectors':len(vectors),
             'first_document_norm':math.sqrt(sum(x*x for x in vectors[0])),
             'collection_configuration':backup['configuration']}
save_json_atomic(ROOT/'embedding-and-index-info.json',vector_info)
print(json.dumps(vector_info,ensure_ascii=False))
def shapes(value,path='',depth=0):
    if depth>8:return
    if isinstance(value,dict):
        print(path,'keys',list(value.keys())[:18])
        for k,v in value.items():
            if isinstance(v,(dict,list)):shapes(v,path+'/'+k,depth+1)
    elif isinstance(value,list):
        print(path,'list_length',len(value))
        if value:shapes(value[0],path+'/0',depth+1)
shapes(raw)
print(context_text(context_result)[:550])
