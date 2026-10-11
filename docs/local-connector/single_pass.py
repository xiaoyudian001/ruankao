"""Retrieve once, prepare bounded original-page evidence, then generate once."""
import json,re,time,logging
from pathlib import Path
from figures import (select_figures,load_catalog,visual_query,visual_payload,cite_original_pages)
from conversation_rewrite import CLARIFY,answer_context
from answer_citations import normalize_citations

WARNING='\n\n> 本次原页解析未完成，以上为正文检索答案；图中细节请对照原页或稍后重试。'

def focus_calculation(query,selected,refs):
 # A single numerical calculation uses its top original, avoiding an unrelated
 # chapter's alternative variable convention. Explicit comparisons keep both.
 if not selected or selected[0].get('kind')!='formula' or not re.search(r'计算|代入|[=＝]\s*\d',query) or re.search(r'比较|对比|区别|差异|跨章|多(?:个|种)公式|分别计算',query):return selected,refs
 chapter=lambda r:re.match(r'^第\s*[\d一二三四五六七八九十百]+\s*章',r.get('chapter',''))
 anchor=chapter(selected[0])
 if not anchor:return selected[:1],refs
 kept=[r for r in refs if chapter(r) and chapter(r).group().replace(' ','')==anchor.group().replace(' ','')]
 return selected[:1],kept

def prepare_visual(question,query,snapshot,timings):
 selected=select_figures(visual_query(question,query),snapshot['references'],load_catalog(),timings=timings)
 if not selected:return [],{},[]
 selected,source_refs=focus_calculation(visual_query(question,query),selected,snapshot['references'])
 refs=[{**r,'rank':i} for i,r in enumerate(source_refs[:10-len(selected)],1)]
 mark=time.monotonic()
 try:payload,extra=visual_payload(question,refs,selected)
 finally:timings['imagePrepareMs']=timings.get('imagePrepareMs',0)+round((time.monotonic()-mark)*1000)
 return selected,payload,extra

def run_single_pass(local,job,budget=220):
 start=time.monotonic();timings={'answerCalls':0,'questionMs':0,'textRetrievalMs':0,'visualRetrievalMs':0,'visualRerankMs':0,'imagePrepareMs':0,'generationMs':0}
 def measured(name,fn):
  mark=time.monotonic()
  try:return fn()
  finally:timings[name]=timings.get(name,0)+round((time.monotonic()-mark)*1000)
 def remaining():
  seconds=budget-(time.monotonic()-start)
  if seconds<1:raise TimeoutError('Answer budget exhausted')
  return seconds
 plan=measured('questionMs',lambda:local.prepare_conversation(job))
 if plan['route']=='clarification':
  result={'answer':CLARIFY,'references':[]}
 else:
  snapshot=measured('textRetrievalMs',lambda:local.retrieve_evidence(job,plan,timeout=min(130,remaining())))
  fallback=False;selected=[];payload={};extra=[]
  try:selected,payload,extra=prepare_visual(job['question'],plan['query'],snapshot,timings)
  except Exception as error:
   fallback=True;timings['fallbackReason']='image_prepare:'+type(error).__name__;logging.info('Original preparation unavailable: %s',type(error).__name__)
  context=answer_context(job['question'],plan['query'],plan['history'])
  def generate(images,wire):
   timings['answerCalls']+=1
   parsed=measured('generationMs',lambda:local.generate_evidence(job,snapshot,context,images,wire,timeout=min(90 if images else 185,remaining())))
   adopted=set(parsed['usedFigureIds'])
   allowed={r['rank'] for r in wire.get('references',snapshot['references']) if not r.get('figures') or r['figures'][0]['id'] in adopted}
   if any(int(rank) not in allowed for rank in re.findall(r'\[片段(\d+)',parsed['answer'])):raise ValueError('Answer referenced unused evidence')
   return parsed
  try:parsed=generate(selected,payload)
  except Exception as error:
   if not selected:raise
   timings['fallbackReason']='visual_generation:'+type(error).__name__
   logging.info('Single visual generation unavailable: %s',type(error).__name__)
   fallback=True;selected=[];extra=[];payload={};parsed=generate([], {})
  text_refs=payload.get('references',snapshot['references'])
  # The wire contains both text and visual sources. Only adopted originals survive.
  text_refs=[r for r in text_refs if not r.get('figures')]
  used=set(parsed['usedFigureIds'])
  refs=text_refs+[r for r in extra if r['figures'][0]['id'] in used]
  ranks={r['rank'] for r in refs}
  if any(int(rank) not in ranks for rank in re.findall(r'\[片段(\d+)',parsed['answer'])):raise ValueError('Answer referenced unused evidence')
  answer=parsed['answer']
  if not selected:
   normalized=normalize_citations(answer,snapshot['rows'])
   answer=normalized['text']
  answer=cite_original_pages(answer,refs)
  if fallback:answer+=WARNING
  result={'answer':answer,'references':refs}
 timings['totalMs']=round((time.monotonic()-start)*1000)
 return {**result,'retrievalQuery':plan['query'],'rewriteRoute':plan['route'],'timings':timings}

def record_timings(job_id,timings):
 # Local diagnostics contain no questions, history, textbook text or credentials.
 path=Path(__file__).with_name('stage-timings.ndjson')
 with path.open('a',encoding='utf-8') as out:
  out.write(json.dumps({'jobId':job_id,'recordedAt':int(time.time()),**timings},ensure_ascii=False)+'\n')
