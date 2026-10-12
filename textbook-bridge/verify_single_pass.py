"""Real answer/model checks; records sources and stage timings, never secrets."""
import json,time,uuid,sys,logging
from pathlib import Path
from bridge import LocalFlow
from single_pass import run_single_pass
from figure_hybrid import warmup

def main():
 warmup();print('Offline index/reranker warmed',flush=True)
 local=LocalFlow();assert local.single_pass_ready()
 state=json.loads(Path(__file__).with_name('single-pass-flows.json').read_text())
 output=Path('F:/daily/output/sysarch-single-answer/real-verification.json')
 records=[];original_call=local.call;answer_calls=[]
 only=sys.argv[1] if len(sys.argv)>1 else ''
 if only and output.exists():records=[r for r in json.loads(output.read_text(encoding='utf-8')) if (r['kind']=='table' if only=='remaining' else r['kind']!=only)]
 logging.basicConfig(level=logging.INFO,format='%(message)s')
 def call(path,*args,**kwargs):
  if path=='/run/session/'+state['generation']:answer_calls.append(path)
  return original_call(path,*args,**kwargs)
 local.call=call
 cases=[('formula','结合教材解释MTBF、MTTR与网络可用性的公式。如果MTBF=199小时、MTTR=1小时，可用性是多少？请区分原式和计算示例，标注教材出处。','default'),
        ('table','结合教材表2-2及其续表，比较张军与李晓钢对ALPHA和REPORT文件的权限。请对照原表说明R、W、X的含义，给出教材页码。','default'),
        ('text','系统架构设计师有哪些职责？','default'),
        ('followup','他的能力要求有哪些？','complete')]
 for kind,question,mode in cases:
  if only and (kind=='table' if only=='remaining' else kind!=only):continue
  job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'question':question,'retrieval_mode':mode,'history_json':'[]'}
  if kind=='followup':
   previous=next(r for r in records if r['kind']=='text')
   job['history_json']=json.dumps([{'question':previous['question'],'answer':previous['result']['answer']}],ensure_ascii=False)
  before=len(answer_calls);result=run_single_pass(local,job)
  print(json.dumps({'kind':kind,'timings':result['timings']},ensure_ascii=False),flush=True)
  if result['timings']['answerCalls']!=1:
   Path('F:/daily/output/sysarch-single-answer/failed-'+kind+'.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  assert len(answer_calls)-before==1 and result['timings']['answerCalls']==1,'Normal path generated more than once'
  assert result['answer'] and result['references']
  visuals=[f for r in result['references'] for f in r.get('figures',[])]
  if kind=='formula':assert '99.5' in result['answer'] and any(f['pdfPage']==628 for f in visuals)
  if kind=='table':
   assert {55,56}<={f['pdfPage'] for f in visuals}
   assert all(w in result['answer'] for w in ['张军','李晓钢','ALPHA','REPORT','RWX','R-X'])
  if kind in ('text','followup'):assert not visuals
  if kind=='followup':assert result['rewriteRoute']=='rewritten' and '架构设计师' in result['retrievalQuery']
  for r in result['references']:
   if r.get('figures'):assert '[片段'+str(r['rank'])+']' in result['answer']
  records.append({'kind':kind,'question':question,'mode':mode,'result':result})
  output.parent.mkdir(parents=True,exist_ok=True)
  output.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'kind':kind,'success':True,'timings':result['timings'],'query':result['retrievalQuery'],'answer':result['answer']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
