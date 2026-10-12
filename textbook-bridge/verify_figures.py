import json,time,uuid
from pathlib import Path
from bridge import LocalFlow
from figures import enrich_answer,select_figures,load_catalog
job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'question':'结合教材图12-2解释三层C/S与B/S结构，说明图中各层如何交互，并给出教材出处。','retrieval_mode':'default'}
start=time.monotonic();local=LocalFlow();result=local.run_conversation(job)
selected=select_figures(result.get('retrievalQuery') or job['question'],result.get('references',[]),load_catalog())
print(json.dumps({'selected':[{'caption':r['caption'],'page':r['pdfPage']} for r in selected]},ensure_ascii=False),flush=True)
result=enrich_answer(local,job,result)
assert any(r.get('figures') for r in result['references']), 'No actual figure adopted'
assert '后台' in result['answer'] and '浏览器' in result['answer'],result['answer']
record={'elapsed_seconds':round(time.monotonic()-start,2),'result':result}
Path('F:/daily/output/sysarch-figure-rag/real-model-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'success':True,'elapsed':record['elapsed_seconds'],'answer':result['answer']},ensure_ascii=False))
