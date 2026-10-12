"""One real MiniMax call using known, saved textbook evidence."""
import json,sys,time
from urllib.error import HTTPError
from pathlib import Path
from bridge import LocalFlow
root=Path(r'F:\daily\output\sysarch-recall-critique');root.mkdir(parents=True,exist_ok=True)
sample={'id':'verify-recall-critique','front':'MTBF是什么？与MTTR有什么区别？','back':'MTBF 平均故障间隔时间，MTTR 平均恢复前时间。','response':'MTBF是平均故障时间，MTTR也是平均故障间隔时间。',
 'references_json':json.dumps([{'rank':1,'content':'平均恢复前时间（Mean Time To Restoration，MTTR）是随机变量恢复时间的期望值，就是从出现故障到修复成功中间的这段时间。MTTR越短表示易恢复性越好。平均故障间隔时间（Mean Time Between Failures，MTBF）定义为：失效或维护中所需的平均时间，包括故障时间以及检测和维护设备的时间。MTBF=MTTF+MTTR。','label':'教材第308页（PDF第323页）'}],ensure_ascii=False)}
start=time.monotonic();local=LocalFlow();assert local.critique_ready()
try:result=local.run_critique(sample)
except HTTPError as error:
 detail=json.loads(error.read().decode('utf-8'))
 # Error from the critique node only; never log model credentials or whole flows.
 print(json.dumps({'critique_error':detail.get('detail')},ensure_ascii=False)[:3500]);raise SystemExit(1)
assert result['corrections'],result
assert all(p['ranks']==[1] for key in ('correct','missing','corrections') for p in result[key])
record={'model':'MiniMax-M3','temperature':0.1,'elapsed_seconds':round(time.monotonic()-start,2),'result':result}
(root/'real-model-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,ensure_ascii=False))
