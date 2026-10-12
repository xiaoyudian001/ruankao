"""Actual local hybrid candidates and authorized MiniMax original-image answer."""
import json,time,uuid
from pathlib import Path
from bridge import LocalFlow
from figures import load_catalog,enrich_answer,select_figures
from figure_hybrid import search_figures,warmup

def main():
 warmup();print('Offline figure reranker prewarmed',flush=True)
 catalog=load_catalog();queries=['浏览器访问网站时，三层分别做什么？','打开网页后，客户端和后台怎么交互？','在软件开发中，事件从产生到处理要经过哪些环节？']
 traces=[]
 for query in queries:
  result=search_figures(query,[],catalog)
  traces.append({'question':query,**result['trace']})
  print(json.dumps({'question':query,'selected':[{'caption':r['caption'],'page':r['pdfPage']} for r in result['selected']],'seconds':result['trace'].get('seconds')},ensure_ascii=False),flush=True)
  if query==queries[0]:assert any('12-2' in r['caption'] for r in result['selected']),'Natural browser question missed actual three-layer figure'
 assert select_figures('系统架构设计师有哪些职责？',[],catalog)==[]
 assert select_figures('解释MTBF是什么',[],catalog)==[]
 record=Path('F:/daily/output/sysarch-figure-rag/hybrid-verification.json');record.write_text(json.dumps({'traces':traces},ensure_ascii=False,indent=2),encoding='utf-8')
 job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'question':queries[0],'retrieval_mode':'default'}
 start=time.monotonic();local=LocalFlow();text=local.run_conversation(job)
 selected=select_figures(text.get('retrievalQuery') or job['question'],text['references'],catalog)
 answer=enrich_answer(local,job,text,selected=selected)
 assert any('12-2' in f['caption'] for r in answer['references'] for f in r.get('figures',[])),'Model did not adopt the actual three-layer figure'
 assert all(w in answer['answer'] for w in ['浏览器','服务器','数据库']),answer['answer']
 record.write_text(json.dumps({'traces':traces,'webAnswer':answer,'elapsed':round(time.monotonic()-start,2)},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'actualModelSuccess':True,'elapsed':round(time.monotonic()-start,2),'answer':answer['answer']},ensure_ascii=False))
if __name__=='__main__':main()
