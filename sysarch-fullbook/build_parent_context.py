"""Build parent windows without changing children, text, or embeddings."""
import hashlib
import json
from pathlib import Path

from parent_context import build_parent_index
from core import save_json_atomic

ROOT=Path(r'F:\daily\output\sysarch-parent-context')
SNAPSHOT=Path(r'F:\daily\output\sysarch-hybrid-retrieval\body-index-52caca320bbf.json')
ORDER=Path(r'F:\daily\output\sysarch-fullbook-v3-watermark\ingest_rows.json')


def main():
    snapshot_raw=SNAPSHOT.read_bytes();order_raw=ORDER.read_bytes()
    indexed={r['chunk_id']:r for r in json.loads(snapshot_raw)['rows']}
    ordered=[r for r in json.loads(order_raw) if r['section_type']=='body']
    assert set(indexed)=={r['chunk_id'] for r in ordered}
    assert all(r['text']==indexed[r['chunk_id']]['content'] for r in ordered)
    result=build_parent_index([indexed[r['chunk_id']] for r in ordered])
    result['source_snapshot_sha256']=hashlib.sha256(snapshot_raw).hexdigest()
    result['source_order_sha256']=hashlib.sha256(order_raw).hexdigest()
    raw=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    sha=hashlib.sha256(raw).hexdigest();ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f'parent-index-{sha[:12]}.json'
    if path.exists():assert path.read_bytes()==raw
    else:path.write_bytes(raw)
    report={'index_path':str(path),'index_sha256':sha,'children':result['count'],
            'parent_windows':len(result['parents']),'max_children_per_parent':max(len(p['child_ids']) for p in result['parents'].values()),
            'source_order_and_text_verified':True,'embeddings_changed':False}
    save_json_atomic(ROOT/'setup.json',report);print(json.dumps(report))


if __name__=='__main__':main()
