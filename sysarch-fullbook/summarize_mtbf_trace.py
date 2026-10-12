import json
import math
from pathlib import Path
from urllib.request import Request,urlopen
from core import save_json_atomic
from citation_format import source_hint

ROOT=Path(r'F:\daily\output\sysarch-rag-explanation')
QUESTION='解释一下什么是MTBF并指出在教材的哪一页'
raw=json.loads((ROOT/'mtbf-retrieval.json').read_text(encoding='utf-8'))
rows=raw['outputs'][0]['outputs'][0]['artifacts']['retrieve_data']['raw']
request=Request('http://127.0.0.1:11434/api/embed',
    data=json.dumps({'model':'bge-m3:latest','input':QUESTION}).encode('utf-8'),
    headers={'Content-Type':'application/json'})
with urlopen(request,timeout=90) as response: embed=json.load(response)
vector=embed['embeddings'][0]
backup=json.loads(Path(r'F:\daily\output\sysarch-page-citations\backups\SysArchTutorRAGv3-before-dual-pages-vectors.json').read_text(encoding='utf-8'))
stored={meta['chunk_id']:vec for meta,vec in zip(backup['metadatas'],backup['embeddings'])}
results=[]
for rank,row in enumerate(rows,1):
    actual=sum((a-b)**2 for a,b in zip(vector,stored[row['chunk_id']]))
    assert abs(actual+row['_score'])<.00001, (actual,row['_score'])
    excerpt=row['content']
    if 'MTBF' in excerpt:
        start=max(0,excerpt.find('MTBF')-70);excerpt=excerpt[start:start+210]
    else:excerpt=excerpt[:210]
    results.append({'rank':rank,'distance':-row['_score'],'public_score':row['_score'],
                    'source':source_hint(row),'excerpt':excerpt,'chunk_id':row['chunk_id']})
info={'question':QUESTION,'query_vector_dimensions':len(vector),'query_vector_first_six':vector[:6],
      'query_vector_norm':math.sqrt(sum(x*x for x in vector)),'hits':results,
      'observed_body_hits':len(results),'body_total':sum(m['section_type']=='body' for m in backup['metadatas']),
      'scores_recalculated_from_vectors_match':True}
save_json_atomic(ROOT/'mtbf-trace-summary.json',info)
print(json.dumps(info,ensure_ascii=False,indent=2))
