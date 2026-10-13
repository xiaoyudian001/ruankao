"""Validate and update only the existing final-generation component, with a private backup."""
import copy,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'sysarch-fullbook'))
from langflow_api import LangflowAPI
from single_pass_components import generation_code

def main():
 state=json.loads(Path(__file__).with_name('single-pass-flows.json').read_text(encoding='utf-8'));api=LangflowAPI();fid=state['generation']
 flow=api.call('/flows/'+fid);code=generation_code();api.call('/custom_component',{'code':code},'POST')
 backup=Path('F:/daily/output/answer-streaming');backup.mkdir(parents=True,exist_ok=True)
 path=backup/('generation-before-'+str(int(time.time()))+'.json');path.write_text(json.dumps(flow,ensure_ascii=False),encoding='utf-8')
 data=copy.deepcopy(flow['data']);node=next(n for n in data['nodes'] if n['id']=='SingleEvidenceAnswer-SysArch');node['data']['node']['template']['code']['value']=code
 api.call('/flows/'+fid,{'data':data},'PATCH');actual=api.call('/flows/'+fid)['data'];assert actual==data,'Unexpected generation-flow change'
 print(json.dumps({'updated':True,'generation':fid,'backup':str(path),'other_nodes_unchanged':True}))

if __name__=='__main__':main()
