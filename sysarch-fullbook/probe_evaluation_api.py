import sys,json
from pathlib import Path
from langflow_api import LangflowAPI
api=LangflowAPI()
body={'inputs':[{'components':['ChatInput-z2rit'],'input_value':'依据教材，事件驱动架构由哪四个部分组成？各自作用是什么？','type':'chat'}],
      'outputs':['Knowledge-Y8gm2','parser-h3mx9','ChatOutput-QRg8s'],
      'tweaks':{'ChatInput-z2rit':{'should_store_message':False},'ChatOutput-QRg8s':{'should_store_message':False}},
      'stream':False,'session_id':'eval-probe-20261008'}
try:
 result=api.call('/run/advanced/2e38f267-52d8-484f-bc4a-81ad7a2e3436',body,'POST',timeout=180)
 root=Path(r'F:\daily\output\sysarch-rag-evaluation');root.mkdir(exist_ok=True,parents=True)
 (root/'probe-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 def shape(v,path='',depth=0):
  if depth>7:return
  if isinstance(v,dict):
   print(path,list(v))
   for k,x in v.items():
    if isinstance(x,(dict,list)):shape(x,path+'/'+k,depth+1)
  elif isinstance(v,list):
   print(path,'length',len(v))
   for i,x in enumerate(v[:3]):shape(x,path+'/'+str(i),depth+1)
 shape(result)
except Exception as e:print('PROBE_ERROR',type(e).__name__,str(e)[:700]);sys.exit(1)
