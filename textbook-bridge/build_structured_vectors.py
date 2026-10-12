"""Local-only embeddings of source table/formula descriptions."""
import hashlib,json,os
import numpy as np
from structured import DIRECTORY,CATALOG,load_catalog
from figure_hybrid import BOOK_SHA,MODEL,document_fingerprint,document_text,embeddings,model_digest,normalized

def main():
 rows=load_catalog();vectors_path=DIRECTORY/'vectors.npz';manifest_path=DIRECTORY/'vectors.json'
 docs_sha=document_fingerprint(rows);digest=model_digest();catalog_sha=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
 if manifest_path.exists() and vectors_path.exists():
  m=json.loads(manifest_path.read_text(encoding='utf-8'))
  if m.get('documentsSha')==docs_sha and m.get('modelDigest')==digest and m.get('catalogSha')==catalog_sha and m.get('vectorsSha')==hashlib.sha256(vectors_path.read_bytes()).hexdigest():
   print(json.dumps({'cached':True,'count':m['count'],'dimensions':m['dimensions']}));return
 vectors=[]
 for start in range(0,len(rows),8):
  vectors.extend(embeddings([document_text(r) for r in rows[start:start+8]],timeout=90))
  print(json.dumps({'embedded':len(vectors),'total':len(rows)}),flush=True)
 values=normalized(vectors,count=len(rows))
 if model_digest()!=digest:raise ValueError('Model changed during indexing')
 temporary=vectors_path.with_suffix('.tmp.npz');np.savez_compressed(temporary,vectors=values)
 manifest={'bookSha':BOOK_SHA,'model':MODEL,'modelDigest':digest,'catalogSha':catalog_sha,'documentsSha':docs_sha,'count':len(rows),'dimensions':values.shape[1],'vectorsSha':hashlib.sha256(temporary.read_bytes()).hexdigest()}
 manifest_tmp=manifest_path.with_suffix('.tmp.json');manifest_tmp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 os.replace(temporary,vectors_path);os.replace(manifest_tmp,manifest_path)
 print(json.dumps({'cached':False,'count':len(rows),'dimensions':values.shape[1]}))
if __name__=='__main__':main()
