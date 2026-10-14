"""Patch usage collection only; preserve existing Langflow wiring and inputs."""
import copy,json,sys,time,inspect
from pathlib import Path
sys.path.insert(0,'F:/daily/sysarch-fullbook')
from langflow_api import LangflowAPI
from generation_usage_code import failure_transport
from token_usage import generation_error_payload

def patch_code(code):
 if 'usage=new_usage()' in code:
  if 'json.dumps(generation_error_payload(usage,error)' in code:return code
  return failure_transport(inspect.getsource(generation_error_payload)+'\n'+code)
 changes=[
  ('  for attempt in range(2):','  usage=new_usage()\n  for attempt in range(2):'),
  ('consume_model(model,messages,box,qa_kind) if box','consume_model(model,messages,box,qa_kind,usage) if box'),
  ('   raw=raw if isinstance(raw,str) else raw.content','   if not box:add_response(usage,raw,getattr(model,\'model_name\',\'\'))\n   raw=raw if isinstance(raw,str) else raw.content'),
  ('    return Message(text=json.dumps(parsed,ensure_ascii=False))',"    parsed['tokenUsage']=usage\n    return Message(text=json.dumps(parsed,ensure_ascii=False))")]
 for old,new in changes:
  if code.count(old)!=1:raise ValueError('Unexpected generation contract')
  code=code.replace(old,new)
 # Update the embedded streaming implementation without replacing prompts or dispatcher.
 start=code.index('async def consume_model(');end=code.index('\nclass StreamMonitor:',start)
 stream=Path(__file__).with_name('streaming.py').read_text(encoding='utf-8')
 replacement=stream[stream.index('async def consume_model('):stream.index('\nclass StreamMonitor:')]
 code=code[:start]+replacement+code[end:]
 return failure_transport(Path(__file__).with_name('token_usage.py').read_text(encoding='utf-8')+'\n'+code)

def main():
 api=LangflowAPI();state=json.loads(Path(__file__).with_name('single-pass-flows.json').read_text(encoding='utf-8'))
 flow=api.call('/flows/'+state['generation']);data=copy.deepcopy(flow['data']);node=next(n for n in data['nodes'] if n['id']=='SingleEvidenceAnswer-SysArch')
 code=node['data']['node']['template']['code']['value'];updated=patch_code(code)
 if updated==code:print(json.dumps({'alreadyApplied':True}));return
 api.call('/custom_component',{'code':updated},'POST')
 backup=Path('F:/daily/output/token-usage');backup.mkdir(parents=True,exist_ok=True)
 path=backup/('generation-before-'+str(int(time.time()))+'.json');path.write_text(json.dumps(flow,ensure_ascii=False),encoding='utf-8')
 node['data']['node']['template']['code']['value']=updated
 api.call('/flows/'+flow['id'],{'data':data},'PATCH');assert api.call('/flows/'+flow['id'])['data']==data
 print(json.dumps({'flow':flow['id'],'nodes':len(data['nodes']),'edges':len(data['edges']),'backup':str(path)}))

if __name__=='__main__':main()
