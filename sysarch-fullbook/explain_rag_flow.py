"""Read-only inventory of actual QA wiring and non-secret retrieval settings."""
import json
from pathlib import Path
from langflow_api import LangflowAPI
from core import save_json_atomic

ROOT=Path(r'F:\daily\output\sysarch-rag-explanation')
FID='2e38f267-52d8-484f-bc4a-81ad7a2e3436'
SAFE={'mode','knowledge_base','metadata_filter','number_of_results','search_type',
      'include_metadata','include_embeddings','top_k','pattern','template','model_name','temperature','stream',
      'should_store_message','session_id','sender','input_value','system_message',
      'search_query','max_tokens','output_types','text_key','model_kwargs'}

def main():
    api=LangflowAPI();flow=api.call('/flows/'+FID)
    ROOT.mkdir(parents=True,exist_ok=True)
    nodes=[]
    for node in flow['data']['nodes']:
        template=node['data']['node']['template']
        row={'id':node['id'],'type':node['data']['type'],
             'display_name':node['data']['node'].get('display_name'),
             'fields':{key:val.get('value') for key,val in template.items() if key in SAFE}}
        for key in ['model','language_model','model_selection']:
            if key in template:
                val=template[key].get('value')
                row['fields'][key]={k:v for k,v in val.items() if k in {'name','model','provider','id'}} if isinstance(val,dict) else val
        nodes.append(row)
        if 'code' in template:
            (ROOT/(node['id'].replace(' ','_')+'.py')).write_text(template['code']['value'],encoding='utf-8')
    edges=[]
    for edge in flow['data']['edges']:
        handles=edge.get('data',{})
        edges.append({'source':edge['source'],'target':edge['target'],
            'source_field':handles.get('sourceHandle',{}).get('name'),
            'target_field':handles.get('targetHandle',{}).get('fieldName')})
    kb=api.call('/knowledge_bases/SysArchTutorRAGv3')
    kb_safe={key:kb.get(key) for key in ['name','chunks','embedding_provider','embedding_model',
                                     'backend_type','backend_config','column_config']}
    value={'name':flow['name'],'flow_id':FID,'nodes':nodes,'edges':edges,'knowledge_base':kb_safe}
    save_json_atomic(ROOT/'read-only-inventory.json',value)
    print(json.dumps(value,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
