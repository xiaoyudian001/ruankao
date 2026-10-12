"""Build a separate local figure-description index without mutating Chroma."""
import hashlib,json,os
from pathlib import Path
import numpy as np
from figures import load_catalog,CATALOG
from figure_hybrid import BOOK_SHA,MODEL,VECTORS,MANIFEST,document_fingerprint,document_text,embeddings,model_digest,normalized

def main():
 catalog=load_catalog();documents_sha=document_fingerprint(catalog);digest=model_digest();catalog_sha=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
 if MANIFEST.exists() and VECTORS.exists():
  m=json.loads(MANIFEST.read_text(encoding='utf-8'))
  if m.get('documentsSha')==documents_sha and m.get('modelDigest')==digest and m.get('catalogSha')==catalog_sha and m.get('vectorsSha')==hashlib.sha256(VECTORS.read_bytes()).hexdigest():
   print(json.dumps({'cached':True,'count':m['count'],'dimensions':m['dimensions']}));return
 vectors=[]
 for start in range(0,len(catalog),8):
  vectors.extend(embeddings([document_text(r) for r in catalog[start:start+8]],timeout=90))
  print(json.dumps({'embedded':len(vectors),'total':len(catalog)}),flush=True)
 values=normalized(vectors,count=len(catalog))
 if model_digest()!=digest:raise ValueError('Model changed during indexing')
 vector_tmp=VECTORS.with_suffix('.tmp.npz');np.savez_compressed(vector_tmp,vectors=values)
 m={'bookSha':BOOK_SHA,'model':MODEL,'modelDigest':digest,'catalogSha':catalog_sha,'documentsSha':documents_sha,'count':len(catalog),'dimensions':values.shape[1],'vectorsSha':hashlib.sha256(vector_tmp.read_bytes()).hexdigest()}
 manifest_tmp=MANIFEST.with_suffix('.tmp.json');manifest_tmp.write_text(json.dumps(m,indent=2),encoding='utf-8')
 os.replace(vector_tmp,VECTORS);os.replace(manifest_tmp,MANIFEST)
 print(json.dumps({'cached':False,'count':len(catalog),'dimensions':values.shape[1],'index':str(VECTORS)}))
if __name__=='__main__':main()
