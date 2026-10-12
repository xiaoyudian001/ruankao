"""Remove only proven identical temporary pilot duplicates after full ingestion."""
import json
import chromadb
from chromadb.config import Settings
from core import save_json_atomic
from parse_book import ROOT


def reconcile():
    state=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
    assert state['next_page']==729
    expected=set(state['expected_chunk_ids'])
    pilot=json.loads((ROOT/'pilot'/'pages_0018_0030.json').read_text(encoding='utf-8'))
    pilot_ids={r['chunk_id'] for r in pilot}
    client=chromadb.PersistentClient(path=r'C:\Users\78052\.langflow\knowledge_bases\langflow\SysArchTutorRAGv2',
                                    settings=Settings(anonymized_telemetry=False))
    col=client.get_collection('SysArchTutorRAGv2')
    data=col.get(include=['documents','metadatas','embeddings'])
    actual={m['chunk_id'] for m in data['metadatas']}
    extra=actual-expected
    assert not expected-actual
    assert extra==pilot_ids and len(extra)==27
    original={r['chunk_id']:r for r in pilot}
    production={}
    for identifier,doc,meta in zip(data['ids'],data['documents'],data['metadatas']):
        if meta['chunk_id'] in expected:
            key=(doc,meta['pdf_pages'],meta['source_sha256'])
            production.setdefault(key,[]).append(identifier)
    indices=[]
    mapping=[]
    for i,(identifier,doc,meta) in enumerate(zip(data['ids'],data['documents'],data['metadatas'])):
        if meta['chunk_id'] in extra:
            source=original[meta['chunk_id']]
            assert (doc,meta['pdf_pages'],meta['source_sha256'])==(source['text'],source['pdf_pages'],source['source_sha256'])
            match=production.get((doc,meta['pdf_pages'],meta['source_sha256']),[])
            assert len(match)==1
            indices.append(i)
            mapping.append({'temporary_pilot_id':identifier,'production_id':match[0],
                            'text_pages_and_source_identical':True})
    backup={'ids':[data['ids'][i] for i in indices],
            'documents':[data['documents'][i] for i in indices],
            'metadatas':[data['metadatas'][i] for i in indices],
            'embeddings':[data['embeddings'][i].tolist() for i in indices],
            'production_matches':mapping,
            'reason':'Pilot used a range-local offset; fullbook uses the preceding-front-matter global offset.'}
    target=ROOT/'backups'/'SysArchTutorRAGv2-pilot-duplicates-before-cleanup.json'
    save_json_atomic(target,backup)
    assert len(json.loads(target.read_text(encoding='utf-8'))['ids'])==27
    col.delete(ids=backup['ids'])
    remaining=col.get(include=['metadatas'])
    assert {m['chunk_id'] for m in remaining['metadatas']}==expected
    save_json_atomic(ROOT/'pilot'/'reconciliation_verified.json',
                     {'temporary_duplicates_removed':27,'expected_chunks_remaining':len(expected),
                      'source_content_preserved':True,'backup':str(target)})
    print('PILOT_RECONCILED',len(expected),'production chunks; 27 identical temporary duplicates backed up and removed')


if __name__=='__main__':
    reconcile()
