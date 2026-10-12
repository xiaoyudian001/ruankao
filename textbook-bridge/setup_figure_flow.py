import copy,json,sys
from pathlib import Path
sys.path.insert(0,'F:/daily/sysarch-fullbook')
from langflow_api import LangflowAPI
from setup_hybrid_flow import component,edge
from run_rag_evaluation import flow_logic_fingerprint
from figures import visual_component_code
def main():
 api=LangflowAPI();source=api.call('/flows/2e38f267-52d8-484f-bc4a-81ad7a2e3436');before=flow_logic_fingerprint(source['data']);path=Path(__file__).parent/'figure-flow.json'
 node=component(api,visual_component_code(),'TextbookFigureAnswer-SysArch',{'x':500,'y':0},{})
 if path.exists():
  state=json.loads(path.read_text(encoding='utf-8'));flow=api.call('/flows/'+state['flow_id']);flow['data']['nodes']=[node if n['id']==node['id'] else n for n in flow['data']['nodes']];api.call('/flows/'+state['flow_id'],{'data':flow['data']},'PATCH')
 else:
  model=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='LanguageModelComponent-BpTTF'));model['data']['selected_output']='model_output';model['position']={'x':0,'y':300}
  for k,v in {'temperature':.1,'max_tokens':4096,'stream':False,'input_value':'','system_message':''}.items():model['data']['node']['template'][k]['value']=v
  chat=copy.deepcopy(next(n for n in source['data']['nodes'] if n['id']=='ChatInput-z2rit'));chat['data']['node']['template']['should_store_message']['value']=False;chat['position']={'x':0,'y':0}
  flow=api.call('/flows/',{'name':'教材图表问答 · 原图与正文','folder_id':source['folder_id'],'description':'真实图像+同页正文，解释层次关系并保留双页码。','data':{'nodes':[chat,model,node],'edges':[edge(chat['id'],'ChatInput','message',['Message'],node['id'],'payload',['Message'],'str'),edge(model['id'],model['data']['type'],'model_output',['LanguageModel'],node['id'],'vision_model',['LanguageModel'],'other')]}},'POST')
  state={'flow_id':flow['id'],'model':'MiniMax-M3','temperature':.1,'component_id':node['id']};path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 assert before==flow_logic_fingerprint(api.call('/flows/'+source['id'])['data']);print(json.dumps(state,ensure_ascii=False))
if __name__=='__main__':main()
