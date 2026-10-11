"""Source-bound table/formula page retrieval and lazy original-page images."""
import hashlib, io, json, logging, re, time
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from pages import PageRenderer
from figure_hybrid import (ROOT, BOOK_SHA, MODEL, FigureIndex, _load, document_fingerprint,
                          checked_model_digest, query_vector, bounded_rerank, GENERIC)
from hybrid_retrieval import BM25Index, tokenize

DIRECTORY=ROOT/'output/sysarch-structured-rag'
CATALOG=DIRECTORY/'catalog.json'
IMAGES=DIRECTORY/'images'

def table_blocks(text):
 lines=text.splitlines();result=[];i=0
 while i+2<len(lines):
  header=lines[i].strip();separator=lines[i+1].strip()
  if header.startswith('|') and header.endswith('|') and re.fullmatch(r'\|(?:\s*:?-{3,}:?\s*\|)+',separator):
   start=i;i+=2
   while i<len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):i+=1
   if i>start+2:result.append('\n'.join(lines[start:i]))
  else:i+=1
 return result

def formula_lines(text):
 result=[]
 for line in text.splitlines():
  line=line.strip()
  if '<!--' in line or len(line)>240:continue
  # Only standalone mathematical lines, not arbitrary prose containing '='.
  if re.search(r'[=＝∫∑]',line) and re.search(r'[A-Za-zΑ-ω]',line) and len(re.findall(r'[\u4e00-\u9fff]',line))<=2:
   result.append(line)
 return result

def continuation_title(text,tables,previous,page):
 if not tables or not previous or previous['page']!=page-1 or not re.match(r'^\s*[（(]?续表[）)]?',text):return ''
 def header(line):return [re.sub(r'\s+','',cell) for cell in line.strip('|').split('|') if not re.fullmatch(r'[.·…\s]+',cell)]
 if header(tables[0].splitlines()[0])!=header(previous['header']):return ''
 return previous['title']+'（续表；表号依据上一页相同列标题）'

def table_numbers(text):return set(re.findall(r'表\s*(\d+)\s*[-－—]\s*(\d+)(?!\d)',text))

def question_kinds(query):
 kinds=set()
 if re.search(r'公式|计算|积分|上下标|变量|分母|可用性|MTTF',query,re.I) or (re.search('MTBF',query,re.I) and re.search('MTTR',query,re.I)):kinds.add('formula')
 if re.search(r'表(?!示|现|达)|矩阵|单元格|行列|对比|比较|区别|差异|各类|分类|分别.*(?:做|作用|职责|特点)',query):kinds.add('table')
 return kinds

@lru_cache(maxsize=1)
def _catalog(raw):
 data=json.loads(raw)
 if data.get('bookSha')!=BOOK_SHA:raise ValueError('Structured book mismatch')
 rows=data['figures']
 if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate structured identity')
 for r in rows:
  if type(r['pdfPage']) is not int or not 18<=r['pdfPage']<=727 or r['kind'] not in ('table','formula') or not set(r['kinds'])<= {'table','formula'}:raise ValueError('Invalid structured page')
  expected=hashlib.sha256(f'{BOOK_SHA}:structured:{r["pdfPage"]}'.encode()).hexdigest()
  if r['id']!=expected or r['bbox']!=[0,0,1,1]:raise ValueError('Invalid structured source')
 return rows

def load_catalog():return _catalog(CATALOG.read_bytes())

def load_index():
 return _load(CATALOG.read_bytes(),(DIRECTORY/'vectors.json').read_bytes(),(DIRECTORY/'vectors.npz').read_bytes())

def topic_rows(query,rows):
 # Formula abbreviations are exact scientific identifiers, not generic words
 # such as "calculate". Do not replace a requested variable with another metric.
 terms=set(re.findall(r'(?<![A-Za-z0-9_])[A-Z][A-Z0-9_]{1,}(?![A-Za-z0-9_])',query))-{'PDF','OCR'}
 if len(terms)<2:return rows
 return [r for r in rows if all(re.search(r'(?<![A-Za-z0-9_])'+re.escape(term)+r'(?![A-Za-z0-9_])',r['context'],re.I) for term in terms)]

def fallback(query,refs,rows,limit=2):
 terms=set(tokenize(query))-GENERIC;pages={p for r in refs for p in r.get('pdfPages',[])}
 source=[{'chunk_id':r['id'],'content':r['caption']+'\n'+r['context'],'chapter':r['chapter'],'source_sha256':BOOK_SHA,'pdf_pages':str(r['pdfPage']),'section_type':'body','figure':r} for r in rows]
 hits=BM25Index(source).search(query,20);ranked=[]
 for hit in hits:
  row=hit['figure'];overlap=terms&(set(tokenize(row['context']))-GENERIC)
  if row['pdfPage'] not in pages or len(overlap)<2:continue
  ranked.append(row)
 return ranked[:limit]

def select_structured(query,refs,catalog=None,limit=2):
 wanted=question_kinds(query)
 if not wanted:return []
 rows=load_catalog() if catalog is None else catalog
 rows=[{**r,'kind':'formula' if 'formula' in wanted and 'formula' in r['kinds'] else 'table'} for r in rows if wanted&set(r['kinds'])];limit=max(0,min(2,limit))
 requested=table_numbers(query)
 if requested:
  return [r for r in rows if requested&table_numbers(r['caption'])][:limit]
 if 'formula' in wanted:rows=topic_rows(query,rows)
 if not rows:return []
 try:
  index,m=load_index()
  if document_fingerprint(index.catalog)!=m['documentsSha']:raise ValueError('Stale structured catalog')
  digest=checked_model_digest(int(time.monotonic()//30))
  if digest!=m['modelDigest']:raise ValueError('Structured embedding model changed')
  ids={r['id'] for r in rows};positions=[i for i,r in enumerate(index.catalog) if r['id'] in ids]
  subset=FigureIndex([index.catalog[i] for i in positions],index.vectors[positions])
  pool=subset.candidates(query,query_vector(query,digest),limit=8)
  if not pool:return []
  scores=bounded_rerank(query,pool)['scores']
  if len(scores)!=len(pool) or not np.isfinite(scores).all():raise ValueError('Invalid structured scores')
  pages={p for ref in refs for p in ref.get('pdfPages',[])};terms=set(tokenize(query))-GENERIC
  selected=[]
  for row,score in sorted(zip(pool,scores),key=lambda pair:-pair[1]):
   cosine=row.get('dense_score') or 0;rank=row.get('dense_rank') or 999
   meaningful=terms&(set(tokenize(row['figure']['context']))-GENERIC)
   strong=score>=0 and cosine>=.45
   strong=strong or (score>=-3 and cosine>=.62 and rank<=3 and meaningful)
   strong=strong or (score>=-2 and cosine>=.5 and row['figure']['pdfPage'] in pages and len(meaningful)>=2)
   if strong:selected.append(row['figure'])
  by_id={r['id']:r for r in rows}
  return [by_id[r['id']] for r in selected[:limit]]
 except Exception as error:
  logging.info('Structured index fallback: %s',type(error).__name__)
  return fallback(query,refs,rows,limit)

def materialize(records):
 if len(records)>2:raise ValueError('Too many structured originals')
 for r in records:
  if type(r.get('pdfPage')) is not int or not 18<=r['pdfPage']<=727 or r.get('kind') not in ('table','formula') or r.get('bbox')!=[0,0,1,1]:raise ValueError('Invalid original page')
  if r.get('id')!=hashlib.sha256(f'{BOOK_SHA}:structured:{r["pdfPage"]}'.encode()).hexdigest():raise ValueError('Original page identity mismatch')
 if not records:return []
 renderer=PageRenderer();IMAGES.mkdir(parents=True,exist_ok=True);result=[]
 for r in records:
  # Render the checked PDF afresh through the original page source, rather than
  # accepting a user/catalog-supplied image path or a previously modified crop.
  with Image.open(io.BytesIO(renderer.render(r['pdfPage'],refresh=True))) as page:
   output=io.BytesIO();page.convert('RGB').save(output,format='PNG');raw=output.getvalue()
  if len(raw)>3*1024*1024:raise ValueError('Structured original image too large')
  path=IMAGES/f'{r["id"]}.png';path.write_bytes(raw)
  result.append({**r,'path':str(path),'imageSha':hashlib.sha256(raw).hexdigest()})
 return result
