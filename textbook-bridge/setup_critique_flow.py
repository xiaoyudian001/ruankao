"""Create one dedicated critique companion using existing MiniMax configuration."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,r'F:\daily\sysarch-fullbook')
from langflow_api import LangflowAPI
from setup_hybrid_flow import component,edge
from run_rag_evaluation import flow_logic_fingerprint
from critique import COMPONENT_CODE
ROOT=Path(__file__).parent
def main():
 api=LangflowAPI();source=api.call('/flows/2e38f267-52d8-484f-bc4a-81ad7a2e3436');before=flow_logic_fingerprint(source['data'])
 statepath=ROOT/'critique-flow.json'
 if statepath.exists():
  state=json.loads(statepath.read_text(encoding='utf-8'));flow=api.call('/flows/'+state['flow_id'])
  reviewer=component(api,COMPONENT_CODE,'RecallCritique-SysArch',{'x':500,'y':0},{})
  flow['data']['nodes']=[reviewer if n['id']=='RecallCritique-SysArch' else n for n in flow['data']['nodes']]
  api.call('/flows/'+state['flow_id'],{'data':flow['data']},'PATCH')
  assert flow_logic_fingerprint(api.call('/flows/'+source['id'])['data'])==before
  print(json.dumps({'flow_id':flow['id'],'component_updated':True}));return
 model=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='LanguageModelComponent-BpTTF'))
 model['position']={'x':0,'y':350};model['data']['selected_output']='model_output'
 template=model['data']['node']['template']
 for key,value in {'temperature':0.1,'max_tokens':4096,'input_value':'','system_message':'','stream':False}.items():
  if key in template:template[key]['value']=value
 chat=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='ChatInput-z2rit'));chat['position']={'x':0,'y':0};chat['data']['node']['template']['should_store_message']['value']=False
 reviewer=component(api,COMPONENT_CODE,'RecallCritique-SysArch',{'x':500,'y':0},{})
 data={'nodes':[chat,model,reviewer],'edges':[edge(chat['id'],'ChatInput','message',['Message'],reviewer['id'],'payload',['Message'],'str'),edge(model['id'],model['data']['type'],'model_output',['LanguageModel'],reviewer['id'],'review_model',['LanguageModel'],'other')],'viewport':{'x':0,'y':0,'zoom':0.8}}
 flow=api.call('/flows/',{'name':'教材主动回忆 · AI点评','description':'MiniMax对照已保存的教材片段点评回忆，不改变自评排期。','folder_id':source['folder_id'],'data':data},'POST')
 assert flow_logic_fingerprint(api.call('/flows/'+source['id'])['data'])==before
 state={'flow_id':flow['id'],'model':'MiniMax-M3','temperature':0.1,'component_id':'RecallCritique-SysArch','original_flow_unchanged':True}
 statepath.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(state,ensure_ascii=False))
if __name__=='__main__':main()
