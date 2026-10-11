"""Create/update companion flows, preserving all existing answer flows."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,'F:/daily/sysarch-fullbook')
from langflow_api import LangflowAPI
from setup_hybrid_flow import component,edge
from run_rag_evaluation import flow_logic_fingerprint
from single_pass_components import SNAPSHOT_CODE,generation_code

SOURCES={'default':'2e38f267-52d8-484f-bc4a-81ad7a2e3436','complete':'ce82698e-54b8-4360-8a11-6f6c4f43f5ff'}
STATE=Path(__file__).with_name('single-pass-flows.json')
BACKUPS=Path('F:/daily/output/sysarch-single-answer');BACKUPS.mkdir(parents=True,exist_ok=True)

def main():
 api=LangflowAPI();sources={m:api.call('/flows/'+fid) for m,fid in SOURCES.items()}
 visual=api.call('/flows/'+json.loads(Path(__file__).with_name('figure-flow.json').read_text())['flow_id'])
 protected={f['id']:flow_logic_fingerprint(f['data']) for f in [*sources.values(),visual]}
 state=json.loads(STATE.read_text()) if STATE.exists() else {'retrieval':{}}
 def persist():STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 def save(key,body):
  fid=state['retrieval'].get(key) if key in SOURCES else state.get(key)
  if fid:api.call('/flows/'+fid,{'data':body['data']},'PATCH')
  else:
   created=api.call('/flows/',body,'POST');fid=created['id']
   if key in SOURCES:state['retrieval'][key]=fid
   else:state[key]=fid
   persist()
  return fid
 for mode,source in sources.items():
  (BACKUPS/(mode+'-source.json')).write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')
  data=copy.deepcopy(source['data'])
  excluded={'LanguageModelComponent-BpTTF','FinalAnswerCleaner-SysArch','ChatOutput-QRg8s'}
  data['nodes']=[n for n in data['nodes'] if n['id'] not in excluded and n['data']['type']!='note']
  ids={n['id'] for n in data['nodes']}
  data['edges']=[e for e in data['edges'] if e['source'] in ids and e['target'] in ids]
  snap=component(api,SNAPSHOT_CODE,'EvidenceSnapshot-SysArch',{'x':1250,'y':1200},{})
  data['nodes'].append(snap)
  parent=next(n for n in data['nodes'] if n['id']=='TextbookParentContext-SysArch')
  prompt=next(n for n in data['nodes'] if n['id']=='Prompt Template-fzcHC')
  data['edges']+=[edge(parent['id'],parent['data']['type'],'expanded_context',['Table'],snap['id'],'rows',['DataFrame','Table'],'other'),edge(prompt['id'],prompt['data']['type'],'prompt',['Message'],snap['id'],'text_prompt',['Message'],'other')]
  save(mode,{'name':'教材证据准备 · '+('当前问答' if mode=='default' else '完整检索'),'folder_id':source['folder_id'],'description':'保留原检索、重排和上下文，仅返回证据与提示；无答案生成节点。','data':data})
 source=sources['default']
 text=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='LanguageModelComponent-BpTTF'))
 vision=copy.deepcopy(next(n for n in visual['data']['nodes'] if n['id']=='LanguageModelComponent-BpTTF'))
 vision['id']='SingleVisionModel-SysArch';vision['data']['id']=vision['id']
 for n,y in [(text,200),(vision,500)]:
  n['data']['selected_output']='model_output';n['position']={'x':0,'y':y}
  n['data']['node']['template']['input_value']['value']='';n['data']['node']['template']['system_message']['value']=''
 chat=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='ChatInput-z2rit'));chat['position']={'x':0,'y':0};chat['data']['node']['template']['should_store_message']['value']=False
 gen=component(api,generation_code(),'SingleEvidenceAnswer-SysArch',{'x':600,'y':0},{})
 data={'nodes':[chat,text,vision,gen],'edges':[edge(chat['id'],'ChatInput','message',['Message'],gen['id'],'payload',['Message'],'str')]+[edge(n['id'],n['data']['type'],'model_output',['LanguageModel'],gen['id'],field,['LanguageModel'],'other') for n,field in [(text,'text_model'),(vision,'vision_model')]]}
 save('generation',{'name':'教材最终作答 · 一次生成','folder_id':source['folder_id'],'description':'正文/原页共享一次生成入口；使用原MiniMax模型配置。','data':data})
 for fid,fingerprint in protected.items():assert flow_logic_fingerprint(api.call('/flows/'+fid)['data'])==fingerprint,'Original flow changed'
 print(json.dumps({**state,'original_flows_unchanged':True},ensure_ascii=False))
if __name__=='__main__':main()
