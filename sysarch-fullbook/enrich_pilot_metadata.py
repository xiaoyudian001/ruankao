import json
from pathlib import Path
import chromadb
from chromadb.config import Settings
from parse_book import ROOT
from core import save_json_atomic

path=Path(r'C:\Users\78052\.langflow\knowledge_bases\langflow\SysArchTutorRAGv2')
client=chromadb.PersistentClient(path=str(path),settings=Settings(anonymized_telemetry=False))
collection=client.get_collection('SysArchTutorRAGv2')
data=collection.get(include=['metadatas'])
assert len(data['ids'])==27, 'Pilot metadata enrichment is limited to the verified 27 rows'
metadata=[]
for original in data['metadatas']:
    row=dict(original)
    assert row['section_type']=='body' and 18<=int(row['pdf_page_start'])<=int(row['pdf_page_end'])<=30
    row['source_metadata']=json.dumps({'section_type':row['section_type'],'chunk_id':row['chunk_id']},ensure_ascii=False)
    metadata.append(row)
collection.update(ids=data['ids'],metadatas=metadata)
verify=collection.get(include=['metadatas'])
assert all(json.loads(m['source_metadata'])['chunk_id']==m['chunk_id'] for m in verify['metadatas'])
save_json_atomic(ROOT/'pilot'/'portable_metadata_verification.json',{'count':27,'filter_tags_verified':True})
print('Pilot metadata filters verified for 27 existing chunks; no text/vector or count changes.')
