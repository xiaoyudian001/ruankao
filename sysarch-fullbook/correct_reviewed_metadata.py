"""Apply only corrections verified against rendered original PDF pages."""
import json
import numpy as np
import chromadb
from chromadb.config import Settings
from core import save_json_atomic
from parse_book import ROOT


def correct():
    progress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
    assert progress['state']=='complete'
    client=chromadb.PersistentClient(path=r'C:\Users\78052\.langflow\knowledge_bases\langflow\SysArchTutorRAGv2',
                                    settings=Settings(anonymized_telemetry=False))
    col=client.get_collection('SysArchTutorRAGv2')
    data=col.get(include=['metadatas'])
    corrections=[('第9章软件可拿丁靠性基础知识','第9章软件可靠性基础知识',320,'chapter09_title.png'),
                 ('第17章 7章通信系统架构设计理论与实践','第17章通信系统架构设计理论与实践',614,'chapter17_title.png')]
    changes=[]
    for identifier,metadata in zip(data['ids'],data['metadatas']):
        matched=[r for r in corrections if r[0] in metadata.get('chapter','')]
        if matched:
            corrected=dict(metadata)
            for old,new,page,evidence in matched:
                corrected['chapter']=corrected['chapter'].replace(old,new)
            changes.append({'id':identifier,'before':metadata,'after':corrected,
                            'verified_original_pdf_page':matched[0][2],'evidence':matched[0][3]})
    if changes:
        ids=[r['id'] for r in changes]
        before=col.get(ids=ids,include=['documents','embeddings'])
        save_json_atomic(ROOT/'reviewed_metadata_corrections.json',changes)
        col.update(ids=ids,metadatas=[r['after'] for r in changes])
        after=col.get(ids=ids,include=['documents','embeddings','metadatas'])
        assert before['ids']==after['ids'] and before['documents']==after['documents']
        assert np.array_equal(before['embeddings'],after['embeddings'])
        assert all(old not in r.get('chapter','') for r in after['metadatas'] for old,_,_,_ in corrections)
        assert col.count()==progress['verified_chunks']
    print(json.dumps({'reviewed_chapter_metadata_corrections':len(changes),
                      'documents_and_vectors_preserved':True},ensure_ascii=False))


if __name__=='__main__':
    correct()
