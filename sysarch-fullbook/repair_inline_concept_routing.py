"""Synchronize only shared reference resolution code in existing conversation components."""
import asyncio
import copy
import json
from pathlib import Path

from core import save_json_atomic
from langflow_api import LangflowAPI

ROOT=Path(r'F:\daily\output\sysarch-conversation-fix-20261010')
# Answer-context clones call only answer_context(), which is unchanged. Patch the active rewriter only.
TARGETS=[('rewrite','61c7f5f7-90b8-49cd-bc25-20b6168586db','ConversationRewrite-SysArch')]


def main():
    api=LangflowAPI()
    before=(ROOT/'conversation_rewrite-before.py').read_text(encoding='utf-8')
    after=Path(__file__).with_name('conversation_rewrite.py').read_text(encoding='utf-8')
    originals={};updated={};checks=[]
    for label,fid,nid in TARGETS:
        saved=api.call('/flows/'+fid)
        original=saved['data'];candidate=copy.deepcopy(original)
        node=next(n for n in candidate['nodes'] if n['id']==nid)
        code=node['data']['node']['template']['code']['value']
        assert code.startswith(before),'Shared helper differs; inspect before updating '+label
        replacement=after+code[len(before):]
        compile(replacement,'<updated-conversation>','exec')
        node['data']['node']['template']['code']['value']=replacement
        reverted=copy.deepcopy(candidate)
        next(n for n in reverted['nodes'] if n['id']==nid)['data']['node']['template']['code']['value']=code
        assert reverted==original,'Unexpected change outside shared helper'
        backup=ROOT/(label+'-flow-before.json')
        if backup.exists():
            assert json.loads(backup.read_text(encoding='utf-8'))['data']==original,'Existing backup differs'
        else:
            save_json_atomic(backup,saved)
        originals[label]=original;updated[label]=candidate
    applied=[]
    try:
        for label,fid,nid in TARGETS:
            assert api.call('/flows/'+fid)['data']==originals[label],'Concurrent edit'
            api.call('/flows/'+fid,{'data':updated[label]},'PATCH');applied.append(label)
            saved=api.call('/flows/'+fid)['data']
            assert saved==updated[label]
            checks.append({'flow':label,'only_shared_helper_changed':True})
    except Exception:
        for label,fid,nid in reversed(TARGETS):
            if label in applied and api.call('/flows/'+fid)['data']==updated[label]:
                api.call('/flows/'+fid,{'data':originals[label]},'PATCH')
        raise
    # Exercise the saved rewriter. A resolved inline label must not require a model invocation.
    node=next(n for n in updated['rewrite']['nodes'] if n['id']=='ConversationRewrite-SysArch')
    code=node['data']['node']['template']['code']['value'];scope={}
    exec(compile(code,'<saved-rewriter>','exec'),scope)
    rewriter=scope['TextbookConversationRewrite'](_code=code)
    q='结合教材 详细解释一下这个概念【ADM是架构开发方法（Architecture Development Method）】'
    rewriter.set(question=q,history_json='[]')
    resolved=asyncio.run(rewriter.resolve()).data
    assert resolved['route']=='direct' and resolved['query']==q
    save_json_atomic(ROOT/'activation.json',{'flows':checks,'saved_rewriter_route':resolved['route'],
                                           'flow_wiring_and_model_settings_unchanged':True})
    print(json.dumps({'updated_flows':checks,'saved_rewriter_route':resolved['route']},ensure_ascii=False))


if __name__=='__main__':
    main()
