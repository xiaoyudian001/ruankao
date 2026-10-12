"""Run the user's exact explicit-target question through the website's local bridge path."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,r'F:\daily\textbook-bridge')
from bridge import LocalFlow
from conversation_rewrite import CLARIFY


def main():
    question='结合教材 详细解释一下这个概念【ADM是架构开发方法（Architecture Development Method）】'
    start=time.monotonic()
    result=LocalFlow().run_conversation({'question':question,'session_id':'verify-inline-adm-20261010',
                                      'history_json':'[]','retrieval_mode':'complete'})
    result['question']=question
    result['elapsed_seconds']=round(time.monotonic()-start,2)
    assert result['rewriteRoute']=='direct' and result['retrievalQuery']==question
    assert result['answer']!=CLARIFY and result['references'], 'No actual retrieved answer'
    root=Path(r'F:\daily\output\sysarch-conversation-fix-20261010')
    (root/'live-adm-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'route':result['rewriteRoute'],'source_count':len(result['references']),
                      'elapsed_seconds':result['elapsed_seconds'],'answer_start':result['answer'][:350]},ensure_ascii=False))


if __name__=='__main__':
    main()
