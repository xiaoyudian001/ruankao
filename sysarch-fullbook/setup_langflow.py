import copy
import json
from pathlib import Path
from core import save_json_atomic
from langflow_api import LangflowAPI
from parse_book import ROOT

def backup_vectors(api,kb,folder):
    import chromadb
    from chromadb.config import Settings
    config=api.call('/knowledge_bases/'+kb)
    path=Path(r'C:\Users\78052\.langflow\knowledge_bases\langflow')/kb
    assert path.is_dir()
    client=chromadb.PersistentClient(path=str(path),settings=Settings(anonymized_telemetry=False))
    col=client.get_collection(kb)
    data=col.get(include=['documents','metadatas','embeddings'])
    backup={'knowledge_base':config,'collection_name':kb,'collection_metadata':col.metadata,
            'configuration':col.configuration,
            'ids':data['ids'],'documents':data['documents'],'metadatas':data['metadatas'],
            'embeddings':data['embeddings'].tolist()}
    assert len(backup['ids'])==config['chunks']
    save_json_atomic(folder/(kb+'-vectors.json'),backup)
    # Restore to a separate workspace database to verify the logical backup.
    restore_path=folder/(kb+'-restore-check')
    trial=chromadb.PersistentClient(path=str(restore_path),settings=Settings(anonymized_telemetry=False))
    restored=trial.get_or_create_collection(kb,metadata=col.metadata,configuration=col.configuration)
    if backup['ids']:
        restored.upsert(ids=backup['ids'],documents=backup['documents'],metadatas=backup['metadatas'],embeddings=backup['embeddings'])
    verify=restored.get(include=['documents','metadatas','embeddings'])
    by_id={v:(d,m,e) for v,d,m,e in zip(verify['ids'],verify['documents'],verify['metadatas'],verify['embeddings'])}
    import numpy as np
    for v,d,m,e in zip(backup['ids'],backup['documents'],backup['metadatas'],backup['embeddings']):
        actual=by_id[v]
        assert actual[0]==d and actual[1]==m and np.array_equal(np.asarray(actual[2],dtype='float32'),np.asarray(e,dtype='float32'))
    save_json_atomic(folder/(kb+'-backup-verification.json'),{'count':len(by_id),'restored_contents_metadata_vectors_match':True})
    return config

def setup():
    api=LangflowAPI()
    folder=ROOT/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    saved=[]
    for fid in ['35d77167-24a6-4876-8c2d-0786a32ca259','2e38f267-52d8-484f-bc4a-81ad7a2e3436']:
        flow=api.call('/flows/'+fid)
        path=folder/(flow['name']+'-before-v2.json')
        if not path.exists():
            save_json_atomic(path,flow)
        saved.append(flow)
    if not (folder/'SysArchTutorRAGv1-vectors.json').exists():
        backup_vectors(api,'SysArchTutorRAGv1',folder)
    config_path=ROOT/'langflow_setup.json'
    if config_path.exists():
        return json.loads(config_path.read_text(encoding='utf-8'))
    models=api.call('/model_options/embedding')
    model=next(m for m in models if m['name']=='bge-m3:latest' and m['provider']=='Ollama')
    columns=[{'column_name':'text','vectorize':True,'identifier':False},
             {'column_name':'chunk_id','vectorize':False,'identifier':True}]
    kb=api.call('/knowledge_bases',{'name':'SysArchTutorRAGv2','embedding_provider':'Ollama',
                                   'embedding_model':'bge-m3:latest','model_selection':model,
                                   'column_config':columns,'backend_type':'chroma','backend_config':{}},'POST')
    code=Path(__file__).with_name('batch_reader_component.py').read_text(encoding='utf-8')
    compiled=api.call('/custom_component',{'code':code},'POST')
    front=compiled['data']
    front['template']['code']['value']=code
    sid='FullBookBatchReader-SysArch'
    reader={'id':sid,'type':'genericNode','position':{'x':150,'y':200},
            'data':{'id':sid,'type':compiled['type'],'node':front,'showNode':True,'selected_output':'rows'}}
    old=next(n for n in saved[0]['data']['nodes'] if n['id']=='Knowledge-QSjSJ')
    target=copy.deepcopy(old)
    tid='Knowledge-FullBook'
    target['id']=tid
    target['data']['id']=tid
    target['position']={'x':750,'y':200}
    template=target['data']['node']['template']
    template['knowledge_base']['value']='SysArchTutorRAGv2'
    template['mode']['value']='Ingest'
    template['column_config']['value']=columns
    template['allow_duplicates']['value']=False
    original_edge=next(e for e in saved[0]['data']['edges'] if e['target']=='Knowledge-QSjSJ')
    edge=copy.deepcopy(original_edge)
    edge['source'],edge['target']=sid,tid
    edge['data']['sourceHandle']={'id':sid,'dataType':compiled['type'],'name':'rows','output_types':front['outputs'][0]['types']}
    edge['data']['targetHandle']['id']=tid
    encode=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('"','œ')
    edge['sourceHandle']=encode(edge['data']['sourceHandle'])
    edge['targetHandle']=encode(edge['data']['targetHandle'])
    edge['id']='reactflow__edge-'+sid+edge['sourceHandle']+'-'+tid+edge['targetHandle']
    data={'nodes':[reader,target],'edges':[edge],'viewport':{'x':0,'y':0,'zoom':.8}}
    flow=api.call('/flows/',{'name':'教材全书分批入库（带页码）',
                           'description':'从本机已解析分片追加正式知识库；解析进度保存在sysarch-fullbook-v2目录。',
                           'folder_id':saved[0]['folder_id'],'data':data},'POST')
    setup_value={'flow_id':flow['id'],'knowledge_base':'SysArchTutorRAGv2','reader_node_id':sid,'knowledge_node_id':tid}
    save_json_atomic(config_path,setup_value)
    save_json_atomic(ROOT/'教材全书分批入库-流程.json',flow)
    print(json.dumps(setup_value,ensure_ascii=False),flush=True)
    return setup_value

if __name__=='__main__':
    setup()
