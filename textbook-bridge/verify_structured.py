"""Actual trusted original-page/model validation; no credentials saved."""
import json,re,time,uuid,sys
from pathlib import Path
from bridge import LocalFlow
from figures import enrich_answer,select_figures,visual_query,load_catalog as figures_catalog
from figure_hybrid import warmup
from structured import select_structured,load_catalog,materialize

def main():
 warmup();catalog=load_catalog();print('Local structured model ready',flush=True)
 local=LocalFlow();records=[]
 output_path=Path('F:/daily/output/sysarch-structured-rag/real-model-verification.json')
 table_only='--table-only' in sys.argv
 if table_only:records=[r for r in json.loads(output_path.read_text(encoding='utf-8')) if r['kind']!='table']
 questions=[
  ('formula','结合教材解释MTBF、MTTR与网络可用性的公式。如果MTBF=199小时、MTTR=1小时，可用性是多少？请区分原式和计算示例，标注教材出处。'),
  ('table','结合教材表2-2及其续表，比较张军与李晓钢对ALPHA和REPORT文件的权限。请对照原表说明R、W、X的含义，给出教材页码。')]
 for kind,question in questions:
  if table_only and kind!='table':continue
  job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'question':question,'retrieval_mode':'default'}
  start=time.monotonic();result=local.run_conversation(job)
  selected=select_structured(visual_query(question,result.get('retrievalQuery')),result['references'],catalog)
  print(json.dumps({'kind':kind,'selected':[{'caption':r['caption'],'page':r['pdfPage']} for r in selected]},ensure_ascii=False),flush=True)
  if kind=='formula':assert 628 in [r['pdfPage'] for r in selected],'Availability source page not recalled'
  else:assert {55,56}=={r['pdfPage'] for r in selected},'Continuation omitted'
  answer=enrich_answer(local,job,result,selected=materialize(selected))
  used=[f for r in answer['references'] for f in r.get('figures',[])]
  assert used and all(f['kind']==kind for f in used), 'Original structured source not adopted'
  assert len(used)<=2 and len(answer['references'])<=10
  if kind=='formula':
   assert '99.5' in answer['answer'] and '示例' in answer['answer'],answer['answer']
   assert any(f['pdfPage']==628 for f in used)
  else:
   assert all(word in answer['answer'] for word in ['张军','李晓钢','ALPHA','REPORT']),answer['answer']
   assert any(f['pdfPage']==56 for f in used)
   assert not re.search(r'不能同时.{0,8}(?:授予|授权)|写入权不能',answer['answer']), 'Invented mutual-exclusion rule'
  records.append({'kind':kind,'question':question,'elapsed':round(time.monotonic()-start,2),'result':answer})
  output_path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'kind':kind,'success':True,'elapsed':records[-1]['elapsed'],'answer':answer['answer']},ensure_ascii=False),flush=True)
 # Graph-number and ordinary text routing remains available.
 assert select_figures('解释图12-2',[],figures_catalog())[0]['pdfPage']==427
 assert select_structured('系统架构设计师有哪些职责？',[],catalog)==[]
if __name__=='__main__':main()
