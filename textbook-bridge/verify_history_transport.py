"""Verify the installed history path without storing test chat messages."""
import json
import sqlite3
import time
from pathlib import Path

from bridge import LocalFlow
from conversation_rewrite import bounded_history
from core import save_json_atomic

ROOT=Path(r'F:\daily\output\sysarch-history-transport-20261010')
SAMPLE=[{'question':'什么是架构演化？','answer':'## 软件架构演化\n\n教材定义与"引号"。\t制表\r\n字面量\\n，路径 C:\\notes\\new；数学 \\nu。'}]
QUESTION='结合教材 解释一下 什么是【什么是架构演化？】'

def main():
    local=LocalFlow();report={'nodes':[],'questions':[]}
    # Reuse the completed live run. output_component controls returned outputs,
    # but this Langflow version still executes the entire downstream graph.
    # Avoid another model call just to inspect the formatter.
    with sqlite3.connect('file:C:/Users/78052/AppData/Roaming/com.LangflowDesktop/data/database.db?mode=ro',uri=True) as db:
        row=db.execute('select s.outputs,s.status,t.id from span s join trace t on s.trace_id=t.id where t.session_id=? and s.name=? order by s.start_time desc limit 1',
                       ('history-codec-verify-default','原问题与会话上下文')).fetchone()
    assert row and row[1]=='ok','Live formatter not successful'
    context=json.loads(row[0])['answer_question']['text']
    assert json.dumps(bounded_history(SAMPLE),ensure_ascii=False) in context,'History changed after live parameter processing'
    report['nodes'].append({'mode':'default','history_preserved_through_live_api':True,'trace_id':row[2]})
    report['saved_component_checks']=json.loads((ROOT/'activation.json').read_text(encoding='utf-8'))['flows']
    save_json_atomic(ROOT/'verification.json',report)
    print(json.dumps({'live_component_checks':report['nodes']},ensure_ascii=False),flush=True)
    history=list(SAMPLE)
    for index,mode in enumerate(('default','default','complete'),1):
        started=time.monotonic()
        value=local.run_conversation({'question':QUESTION,'session_id':'history-transport-verification',
            'retrieval_mode':mode,'history_json':json.dumps(history,ensure_ascii=False)})
        assert value['answer'].strip() and '演化' in value['answer'],'Expected topic absent'
        assert value['rewriteRoute']=='direct','Independent question should not invoke rewriter'
        assert value['references'],'Missing source references'
        row={'turn':index,'mode':mode,'success':True,'history_turns':len(bounded_history(history)),
             'seconds':round(time.monotonic()-started,2),'answer_characters':len(value['answer']),
             'reference_count':len(value['references'])}
        report['questions'].append(row);save_json_atomic(ROOT/'verification.json',report)
        history.append({'question':QUESTION,'answer':value['answer']})
        print(json.dumps(row,ensure_ascii=False),flush=True)
    report['passed']=True;save_json_atomic(ROOT/'verification.json',report)

if __name__=='__main__':main()
