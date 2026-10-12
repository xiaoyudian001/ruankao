"""Local text-based semantic figure retrieval; original images are never embedded."""
import hashlib,json,logging,re,sys,time,threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.request import Request,urlopen
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'sysarch-fullbook'))
from hybrid_retrieval import BM25Index,fuse_rrf,tokenize
BOOK_SHA='edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'
MODEL='bge-m3:latest';OLLAMA='http://127.0.0.1:11434'
DIRECTORY=ROOT/'output/sysarch-figure-rag'
VECTORS=DIRECTORY/'figure-vectors.npz';MANIFEST=DIRECTORY/'figure-vectors.json'
_RERANK_EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix='figure-rerank')
_RERANK_LOCK=threading.Lock();_RERANK_PENDING=None
GENERIC=set(tokenize('结合教材详细解释什么怎么为什么概念系统架构结构模型流程关系包括哪些组成部分原文图示图表如下软件开发环节过程'))

def needs_hybrid(query):
 text=re.sub(r'架构设计师|架构师','',query)
 return bool(re.search(r'图|表|架构|结构|模型|流程|拓扑|生命周期|网络|协议|分层|三层|两层|浏览器|服务器|网页|客户端|交互|连接|通信|步骤|部件|组成|环节|过程|流转|传递|事件|分工|路径|画|示意',text,re.I))

def document_text(row):
 return (row['caption']+'\n'+row.get('chapter','')+'\n'+row.get('context',''))[:1800]

def document_fingerprint(catalog):
 records=[{'id':r['id'],'text':document_text(r),'page':r['pdfPage']} for r in catalog]
 return hashlib.sha256(json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def ollama(path,body=None,timeout=8):
 req=Request(OLLAMA+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=timeout) as response:return json.load(response)

def model_digest():
 tags=ollama('/api/tags')['models']
 return next(m['digest'] for m in tags if m['name']==MODEL)

def embeddings(texts,timeout=8):
 result=ollama('/api/embed',{'model':MODEL,'input':texts,'truncate':False,'keep_alive':'10m'},timeout)
 if result.get('model')!=MODEL or len(result.get('embeddings',[]))!=len(texts):raise ValueError('Embedding model or count mismatch')
 return result['embeddings']

def normalized(vectors,count=None,dimensions=None):
 values=np.asarray(vectors,dtype=np.float32)
 if values.ndim!=2 or not values.size or not np.isfinite(values).all() or (count is not None and len(values)!=count) or (dimensions is not None and values.shape[1]!=dimensions):raise ValueError('Invalid vector matrix')
 with np.errstate(over='ignore'):norms=np.linalg.norm(values,axis=1,keepdims=True)
 if not np.isfinite(norms).all() or (norms<1e-8).any():raise ValueError('Invalid vector norm')
 return values/norms

class FigureIndex:
 def __init__(self,catalog,vectors):
  if len({r['id'] for r in catalog})!=len(catalog):raise ValueError('Duplicate figure identity')
  self.catalog=catalog;self.vectors=normalized(vectors,count=len(catalog))
  self.rows=[{'chunk_id':r['id'],'content':document_text(r),'chapter':r.get('chapter',''),'source_sha256':BOOK_SHA,'pdf_pages':str(r['pdfPage']),'section_type':'body','figure':r} for r in catalog]
  # Repeat the original caption, so a whole page does not drown its figure title.
  self.lexical=BM25Index([{**r,'content':(r['figure']['caption']+'\n')*3+r['content']} for r in self.rows])
  self.captions=BM25Index([{**r,'content':r['figure']['caption'],'chapter':''} for r in self.rows])
 def candidates(self,query,vector,limit=8):
  v=normalized([vector],count=1,dimensions=self.vectors.shape[1])[0]
  scores=self.vectors@v
  order=sorted(range(len(scores)),key=lambda i:(-float(scores[i]),self.rows[i]['chunk_id']))[:20]
  dense=[{**self.rows[i],'_score':float(scores[i])} for i in order if scores[i]>=.45]
  canonical={r['chunk_id']:r for r in self.rows}
  terms=set(tokenize(query))-GENERIC
  lexical_query='|'.join(sorted(terms)) or query
  body_hits=self.lexical.search(lexical_query,20);caption_hits=self.captions.search(lexical_query,20)
  body_scores={r['chunk_id']:r['bm25_score'] for r in body_hits};caption_scores={r['chunk_id']:r['bm25_score'] for r in caption_hits}
  lexical_ids=sorted(body_scores.keys()|caption_scores.keys(),key=lambda ident:(-caption_scores.get(ident,0),-body_scores.get(ident,0),ident))[:20]
  lexical=[{**canonical[ident],'bm25_score':body_scores.get(ident,0)+caption_scores.get(ident,0)} for ident in lexical_ids]
  merged=fuse_rrf(dense,lexical,limit=40,constant=60)
  # Keep the first result of both independent routes when the bounded pool is cut.
  protected={r['chunk_id'] for route in (dense,lexical) for r in route[:1]}
  pool=sorted(merged,key=lambda r:(r['chunk_id'] not in protected,-r['rrf_score']))[:limit]
  score_by_id={r['chunk_id']:float(scores[i]) for i,r in enumerate(self.rows)}
  for row in pool:
   if row['dense_score'] is None:row['dense_score']=score_by_id[row['chunk_id']]
   row['caption_matches']=len((set(tokenize(query))-GENERIC)&(set(tokenize(row['figure']['caption']))-GENERIC))
  return pool

@lru_cache(maxsize=1)
def _load(catalog_raw,manifest_raw,vector_raw):
 catalog=json.loads(catalog_raw);m=json.loads(manifest_raw)
 if catalog.get('bookSha')!=BOOK_SHA or m.get('bookSha')!=BOOK_SHA or m.get('model')!=MODEL or m.get('documentsSha')!=document_fingerprint(catalog['figures']) or m.get('catalogSha')!=hashlib.sha256(catalog_raw).hexdigest():raise ValueError('Stale figure documents')
 if hashlib.sha256(vector_raw).hexdigest()!=m.get('vectorsSha'):raise ValueError('Figure vector digest mismatch')
 import io
 with np.load(io.BytesIO(vector_raw),allow_pickle=False) as stored:vectors=stored['vectors']
 normalized(vectors,count=m['count'],dimensions=m['dimensions'])
 return FigureIndex(catalog['figures'],vectors),m

def load_index():
 return _load((DIRECTORY/'catalog.json').read_bytes(),MANIFEST.read_bytes(),VECTORS.read_bytes())

@lru_cache(maxsize=1)
def checked_model_digest(time_bucket):return model_digest()

@lru_cache(maxsize=64)
def query_vector(query,digest):return embeddings([query])[0]

def bounded_rerank(query,pool):
 global _RERANK_PENDING
 from local_rerank_runtime import score_pairs
 with _RERANK_LOCK:
  if _RERANK_PENDING is not None and not _RERANK_PENDING.done():raise TimeoutError('Figure reranker busy')
  _RERANK_PENDING=_RERANK_EXECUTOR.submit(score_pairs,query,pool)
  task=_RERANK_PENDING
 return task.result(timeout=15)

def warmup():
 """Load the reviewed offline model before a user submits a figure question."""
 global _RERANK_PENDING
 load_index()
 from local_rerank_runtime import load_model
 with _RERANK_LOCK:
  if _RERANK_PENDING is None or _RERANK_PENDING.done():_RERANK_PENDING=_RERANK_EXECUTOR.submit(load_model)
  task=_RERANK_PENDING
 task.result(timeout=90)

def relevant_candidate(row,score):
 cosine=row.get('dense_score') or 0
 if score>=0.0 and cosine>=.45:return True
 # Logits are not probabilities. Retain corroborated colloquial queries for the
 # visual model's final relevance check, while rejecting very low local scores.
 strong_semantic=(row.get('dense_rank') or 999)<=3 and cosine>=.62
 strong_caption=(row.get('lexical_rank') or 999)<=3 and row.get('caption_matches',0)>=1 and cosine>=.55
 return score>=-3.0 and (strong_semantic or strong_caption)

def search_figures(query,refs,catalog,limit=2,timings=None):
 started=time.monotonic();index,m=load_index()
 if document_fingerprint(catalog)!=m['documentsSha']:raise ValueError('Catalog differs from index')
 digest=checked_model_digest(int(time.monotonic()//30))
 if digest!=m['modelDigest']:raise ValueError('Embedding model changed')
 pool=index.candidates(query,query_vector(query,digest))
 if not pool:return {'selected':[],'trace':{'method':'hybrid','candidates':[]}}
 mark=time.monotonic()
 try:scored=bounded_rerank(query,pool)
 finally:
  if timings is not None:timings['visualRerankMs']=timings.get('visualRerankMs',0)+round((time.monotonic()-mark)*1000)
 if len(scored['scores'])!=len(pool) or not np.isfinite(scored['scores']).all():raise ValueError('Invalid local figure relevance scores')
 pages={p for r in refs for p in r.get('pdfPages',[])}
 # Page evidence breaks ties; it cannot make a low-relevance candidate pass.
 ranked=sorted(zip(pool,scored['scores']),key=lambda pair:(-pair[1],pair[0]['figure']['pdfPage'] not in pages,-pair[0]['rrf_score']))
 eligible=[(r,float(score)) for r,score in ranked if relevant_candidate(r,score)]
 selected=[r['figure'] for r,_ in eligible[:max(0,min(2,limit))]]
 trace={'method':'bge-m3+bm25+rrf+local-cross-encoder','seconds':round(time.monotonic()-started,3),'rerankModel':scored['model_revision'],'candidates':[{'id':r['chunk_id'],'caption':r['figure']['caption'],'pdfPage':r['figure']['pdfPage'],'denseRank':r['dense_rank'],'lexicalRank':r['lexical_rank'],'cosine':r.get('dense_score'),'rrf':r['rrf_score'],'rerank':float(score)} for r,score in ranked],'selectedIds':[r['id'] for r in selected]}
 return {'selected':selected,'trace':trace}

def select_hybrid(query,refs,catalog,limit=2,timings=None):
 if not needs_hybrid(query):return []
 return search_figures(query,refs,catalog,limit,timings=timings)['selected']
