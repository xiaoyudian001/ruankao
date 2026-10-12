import json,uuid
from pathlib import Path
from urllib.error import HTTPError
from bridge import LocalFlow
previous=json.loads(Path('F:/daily/output/sysarch-single-answer/real-verification.json').read_text(encoding='utf-8'))
refs=next(r['result']['references'] for r in previous if r['kind']=='text')
job={'id':str(uuid.uuid4()),'task_type':'exam'}
try:
 result=LocalFlow().generate_evidence(job,{'references':refs,'textPrompt':'教材资料'},'哪项属于系统架构设计师的职责？A.确认和评估需求 B.只录入数据 C.只做采购 D.不管质量',[],{},timeout=130)
 Path('F:/daily/output/sysarch-exam').mkdir(parents=True,exist_ok=True)
 Path('F:/daily/output/sysarch-exam/generation-only.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({'success':True,'practice':result.get('practice') is not None},ensure_ascii=False))
except HTTPError as exc:
 raw=exc.read().decode('utf-8',errors='replace')
 # Error response contains component diagnostics; redact common credential forms.
 import re
 raw=re.sub(r'(?:sk-|Bearer\s+)[A-Za-z0-9_.-]+','[redacted]',raw)
 print(raw[:3500])
 raise SystemExit(1)
