"""Patch only the shared history codec in the three existing conversation flows."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path

from core import save_json_atomic
from conversation_rewrite import encode_history, bounded_history
from langflow_api import LangflowAPI

ROOT=Path(r'F:\daily\output\sysarch-history-transport-20261010')
TARGETS=[('rewrite','61c7f5f7-90b8-49cd-bc25-20b6168586db','ConversationRewrite-SysArch'),
         ('default','94e0161b-b811-46e4-807a-c5a4c5f05806','ConversationAnswerContext-SysArch'),
         ('complete','f237233c-36bb-4d47-9f3b-fc456b911edb','ConversationAnswerContext-SysArch')]

def codec_block(code):
    start=code.index('def encode_history(') if 'def encode_history(' in code else code.index('def bounded_history(')
    end=code.index('def chapters(',start)
    return start,end

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    api=LangflowAPI()
    shared=Path(__file__).with_name('conversation_rewrite.py').read_text(encoding='utf-8')
    start,end=codec_block(shared);block=shared[start:end]
    old_helper=(ROOT/'conversation_rewrite-before.py').read_text(encoding='utf-8')
    old_start,old_end=codec_block(old_helper);old_block=old_helper[old_start:old_end]
    originals={};updated={};checks=[]
    for label,fid,nid in TARGETS:
        saved=api.call('/flows/'+fid)
        original=saved['data'];candidate=copy.deepcopy(original)
        node=next(n for n in candidate['nodes'] if n['id']==nid)
        code=node['data']['node']['template']['code']['value']
        begin,finish=codec_block(code)
        assert code[begin:finish] in (old_block,block),'Unexpected codec implementation: '+label
        replacement=code[:begin]+block+code[finish:]
        compile(replacement,'<history-transport-'+label+'>','exec')
        node['data']['node']['template']['code']['value']=replacement
        reverted=copy.deepcopy(candidate)
        next(n for n in reverted['nodes'] if n['id']==nid)['data']['node']['template']['code']['value']=code
        assert reverted==original,'Changes outside shared history codec'
        backup=ROOT/(label+'-flow-before.json')
        if not backup.exists():save_json_atomic(backup,saved)
        originals[label]=original;updated[label]=candidate
    applied=[]
    try:
        for label,fid,nid in TARGETS:
            assert api.call('/flows/'+fid)['data']==originals[label],'Concurrent flow edit: '+label
            if updated[label]!=originals[label]:
                api.call('/flows/'+fid,{'data':updated[label]},'PATCH');applied.append(label)
            saved=api.call('/flows/'+fid)['data']
            assert saved==updated[label],'Saved flow differs: '+label
            code=next(n for n in saved['nodes'] if n['id']==nid)['data']['node']['template']['code']['value']
            scope={};exec(compile(code,'<saved-history-codec>','exec'),scope)
            sample=[{'question':'什么是架构演化？','answer':'## 答案\n\n中文"引号"\t制表\r\n路径 C:\\notes\\new，字面量\\n，数学 \\nu。'}]
            wire=encode_history(sample)
            assert scope['bounded_history'](wire)==bounded_history(sample)
            if label=='rewrite':
                component=scope['TextbookConversationRewrite'](_code=code)
                component.set(question='什么是架构演化？',history_json=wire)
                result=asyncio.run(component.resolve()).data
                assert result['route']=='direct' and result['history_count']==1
            else:
                component=scope['TextbookConversationAnswerContext'](_code=code)
                component.set(query='什么是架构演化？',original_question='什么是架构演化？',history_json=wire)
                context=component.build().text
                assert json.dumps(sample,ensure_ascii=False) in context
            checks.append({'flow':label,'codec_only_change':True,'saved_component_verified':True,
                           'code_sha256':hashlib.sha256(code.encode()).hexdigest()})
    except Exception:
        for label,fid,nid in reversed(TARGETS):
            if label in applied and api.call('/flows/'+fid)['data']==updated[label]:
                api.call('/flows/'+fid,{'data':originals[label]},'PATCH')
        raise
    save_json_atomic(ROOT/'activation.json',{'flows':checks,'transport':'history-b64-v1',
                                           'wiring_and_model_settings_unchanged':True})
    print(json.dumps({'updated_flows':checks,'transport':'history-b64-v1'},ensure_ascii=False))

if __name__=='__main__':main()
