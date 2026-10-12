"""Add verified printed-page metadata; keep IDs, text and embeddings byte-identical."""
import copy
import json
from collections import Counter
from pathlib import Path

import chromadb
import numpy as np
from chromadb.config import Settings
from core import save_json_atomic
from printed_page_mapping import ROOT, page_fields

KB='SysArchTutorRAGv3'
CORPUS=Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')

def enrich_cache(path, mapping):
    rows=json.loads(path.read_text(encoding='utf-8'))
    backup=ROOT/'backups'/'cached-files'/path.relative_to(Path(r'F:\daily\output'))
    if not backup.exists(): save_json_atomic(backup,rows)
    for row in rows:
        meta=row.get('metadata',row)
        meta.update(page_fields(meta,mapping))
    save_json_atomic(path,rows)

def apply():
    mapping=json.loads((ROOT/'page-map.json').read_text(encoding='utf-8'))
    cached=json.loads((CORPUS/'final_chunks.json').read_text(encoding='utf-8'))
    client=chromadb.PersistentClient(
        path=str(Path(r'C:\Users\78052\.langflow\knowledge_bases\langflow')/KB),
        settings=Settings(anonymized_telemetry=False))
    col=client.get_collection(KB)
    before=col.get(include=['documents','metadatas','embeddings'])
    assert len(before['ids'])==len(cached)==1675
    # Chroma storage IDs differ between V2/V3; chunk_id is the stable source identifier.
    expected={r['metadata']['chunk_id']:r['content'] for r in cached}
    assert {m['chunk_id'] for m in before['metadatas']}==set(expected)
    assert all(d==expected[m['chunk_id']] for m,d in zip(before['metadatas'],before['documents']))
    backup=ROOT/'backups'/'SysArchTutorRAGv3-before-dual-pages-vectors.json'
    if not backup.exists():
        save_json_atomic(backup,{'collection_name':KB,'collection_metadata':col.metadata,
            'configuration':col.configuration,'ids':before['ids'],'documents':before['documents'],
            'metadatas':before['metadatas'],'embeddings':before['embeddings'].tolist()})
    updated=[]
    for old in before['metadatas']:
        meta=copy.deepcopy(old);meta.update(page_fields(meta,mapping));updated.append(meta)
    for index in range(0,len(updated),200):
        col.update(ids=before['ids'][index:index+200],metadatas=updated[index:index+200])
    after=col.get(include=['documents','metadatas','embeddings'])
    actual={i:(d,m,e) for i,d,m,e in zip(after['ids'],after['documents'],after['metadatas'],after['embeddings'])}
    for i,d,m,e in zip(before['ids'],before['documents'],updated,before['embeddings']):
        result=actual[i]
        assert result[0]==d and result[1]==m
        assert np.array_equal(result[2],e), 'Embedding changed'
    enrich_cache(CORPUS/'final_chunks.json',mapping)
    enrich_cache(CORPUS/'ingest_rows.json',mapping)
    for path in sorted(Path(r'F:\daily\output\sysarch-fullbook-v2\clean_v3_ingest').glob('batch_*.json')):
        enrich_cache(path,mapping)
    stats=Counter(m['book_page_mapping_status'] for m in updated)
    save_json_atomic(ROOT/'metadata-verification.json',{
        'knowledge_base':KB,'chunks':len(actual),'ids_text_and_vectors_unchanged':True,
        'metadata_status_counts':dict(stats),'mapping_version':mapping['version'],
        'backup':str(backup)})
    print('METADATA_VERIFIED',len(actual),dict(stats),flush=True)

if __name__=='__main__': apply()
