"""Run the new exam task against the actual local Langflow/MiniMax pipeline."""
import json,uuid,re
from urllib.error import HTTPError
from pathlib import Path
from bridge import LocalFlow
from single_pass import run_single_pass
local=LocalFlow();state=json.loads(Path(__file__).with_name('single-pass-flows.json').read_text());calls=[];original=local.call
def call(path,*args,**kwargs):
 if path=='/run/session/'+state['generation']:calls.append(path)
 try:return original(path,*args,**kwargs)
 except HTTPError as exc:
  raw=re.sub(r'(?:sk-|Bearer\s+)[A-Za-z0-9_.-]+','[redacted]',exc.read().decode('utf-8',errors='replace'))
  print(raw[:2000],flush=True);raise
local.call=call
job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'task_type':'exam','retrieval_mode':'default','history_json':'[]',
 'question':'下列哪项属于系统架构设计师的职责？（单选）\nA. 确认和评估需求，给出开发规范\nB. 只负责采购服务器，不参与需求评估\nC. 只负责录入业务数据\nD. 不参与早期质量保证\n请结合教材说明各选项。'}
result=run_single_pass(local,job)
out=Path('F:/daily/output/sysarch-exam');out.mkdir(parents=True,exist_ok=True)
(out/'real-verification.json').write_text(json.dumps({'question':job['question'],'result':result},ensure_ascii=False,indent=2),encoding='utf-8')
assert len(calls)==1 and result['timings']['answerCalls']==1
assert result['references'] and result['practice'] and result['practice']['ranks']
assert all(x in result['answer'] for x in ('A','B','C','D'))
assert '需求' in result['answer']
assert re.search(r'\[片段\d+',result['answer']) and not re.search(r'\brank\s*\d',result['answer'],re.I)
assert '\n' not in result['retrievalQuery']
assert not any(r.get('figures') for r in result['references'])
print(json.dumps({'passed':True,'answerCalls':len(calls),'timings':result['timings'],'practiceOptions':len(result['practice']['options']),'answer':result['answer']},ensure_ascii=False),flush=True)
