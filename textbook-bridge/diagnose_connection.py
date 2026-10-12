"""Print bounded connection diagnostics without credentials or user content."""
import json, sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
config=json.loads(sys.stdin.readline())
for label,url,body,headers in [
 ('langflow','http://127.0.0.1:7860/api/v1/auto_login',None,{}),
 ('ollama','http://127.0.0.1:11434/api/tags',None,{}),
 ('site-root',config['site_url']+'/',None,{}),
 ('bridge-heartbeat',config['site_url']+'/api/textbook/bridge',{'action':'heartbeat','ready':True},{'Authorization':'Bearer '+config['secret']})]:
 try:
  req=Request(url,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json','User-Agent':'TextbookConnector/1.0',**headers})
  with urlopen(req,timeout=20) as response:
   response.read()
   print(json.dumps({'check':label,'status':response.status}))
 except HTTPError as error:
  data=error.read(4096).decode('utf-8','replace')
  code='cloudflare-1010' if '1010' in data else ('cloudflare-challenge' if 'Just a moment' in data else ('unauthorized' if 'Unauthorized' in data else 'other'))
  print(json.dumps({'check':label,'status':error.code,'kind':code,'ray':error.headers.get('cf-ray'),'content_type':error.headers.get('Content-Type')}))
 except Exception as error:print(json.dumps({'check':label,'error':type(error).__name__}))
