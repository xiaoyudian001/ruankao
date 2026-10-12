import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE='http://127.0.0.1:7860/api/v1'

class LangflowAPI:
    def __init__(self):
        with urlopen(BASE+'/auto_login',timeout=15) as response:
            self.token=json.load(response)['access_token']

    def call(self,path,body=None,method='GET',timeout=60,_retry_auth=True):
        req=Request(BASE+path,method=method,
                    data=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None,
                    headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with urlopen(req,timeout=timeout) as response:
                return json.load(response)
        except HTTPError as e:
            detail=e.read().decode('utf-8',errors='replace')
            e.close()
            if e.code==401 and _retry_auth:
                with urlopen(BASE+'/auto_login',timeout=15) as response:
                    self.token=json.load(response)['access_token']
                return self.call(path,body,method,timeout,_retry_auth=False)
            raise RuntimeError(f'HTTP {e.code} {path}: {detail[:2500]}') from e

    def chunks(self,kb,chunk_ids=None):
        rows=[]
        page=1
        while True:
            query=''.join('&meta_chunk_id='+value for value in chunk_ids) if chunk_ids else ''
            data=self.call(f'/knowledge_bases/{kb}/chunks?page={page}&limit=100'+query)
            rows.extend(data['chunks'])
            if len(rows)>=data['total']:
                return rows
            page+=1

    def run_ingest(self,flow_id,batch_file,kb='SysArchTutorRAGv2'):
        body={'input_request':{'input_value':'','input_type':'any','output_type':'any',
                               'output_component':'Knowledge-FullBook',
                               'tweaks':{'FullBookBatchReader-SysArch':{'batch_file':str(batch_file)},
                                         'Knowledge-FullBook':{'knowledge_base':kb}},
                               'session_id':'sysarch-fullbook-'+Path(batch_file).stem}}
        return self.call('/run/session/'+flow_id,body,'POST',timeout=240)
