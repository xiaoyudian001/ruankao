import json,unittest
import ast
from pathlib import Path
from unittest.mock import patch
from bridge import LocalFlow, CONVERSATION_FLOWS
from conversation_rewrite import bounded_history

# Execute the installed framework's actual string transformation without
# importing its full application runtime into these unit tests.
def langflow_string(value):
    source=Path(r'C:\Users\78052\AppData\Local\com.LangflowDesktop\.langflow-venv\Lib\site-packages\lfx\utils\util.py')
    tree=ast.parse(source.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='unescape_string')
    scope={}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<langflow-unescape>','exec'),scope)
    return scope['unescape_string'](value)

class ConversationBridgeTest(unittest.TestCase):
    transport_history=[{'question':'什么是架构演化？','answer':'## 架构演化\n\n段落含"引号"、中文、制表\t及回车\r\n代码：C:\\notes\\new，字面量\\n；数学 \\nu。'}]
    def test_answer_history_survives_langflow_string_processing(self):
        local=LocalFlow();received=[]
        def call(path,body=None,**kwargs):
            wire=body['input_request']['tweaks']['ConversationAnswerContext-SysArch']['history_json']
            received.append(bounded_history(langflow_string(wire)))
            return {'outputs':[{'outputs':[{'results':{'message':{'text':'有效教材回答'}}}]}]}
        for mode in ('default','complete'):
            with self.subTest(mode=mode),patch.object(local,'call',side_effect=call):
                result=local.run_conversation({'question':'结合教材解释什么是架构演化？','session_id':'transport-test','retrieval_mode':mode,'history_json':json.dumps(self.transport_history,ensure_ascii=False)})
                self.assertEqual(result['answer'],'有效教材回答')
                self.assertEqual(received[-1],self.transport_history)
    def test_rewrite_history_survives_langflow_string_processing(self):
        local=LocalFlow();received=[]
        def call(path,body=None,**kwargs):
            tweaks=body['input_request']['tweaks']
            node='ConversationRewrite-SysArch' if path.endswith(CONVERSATION_FLOWS['rewrite']) else 'ConversationAnswerContext-SysArch'
            received.append(bounded_history(langflow_string(tweaks[node]['history_json'])))
            if node=='ConversationRewrite-SysArch':
                return {'outputs':[{'outputs':[{'outputs':{'rewrite_result':{'message':{'query':'架构演化的原因是什么？','route':'rewritten'}}}}]}]}
            return {'outputs':[{'outputs':[{'results':{'message':{'text':'有效教材回答'}}}]}]}
        with patch.object(local,'call',side_effect=call):
            result=local.run_conversation({'question':'它的原因是什么？','session_id':'transport-test','history_json':json.dumps(self.transport_history,ensure_ascii=False)})
        self.assertEqual(result['rewriteRoute'],'rewritten')
        self.assertEqual(received,[self.transport_history,self.transport_history])
    def test_rewrite_then_retrieve_preserves_original(self):
        local=LocalFlow();calls=[]
        def call(path,body=None,**kwargs):
            calls.append((path,body))
            if path.endswith(CONVERSATION_FLOWS['rewrite']):
                return {'outputs':[{'outputs':[{'outputs':{'rewrite_result':{'message':{'query':'MTBF和MTTR有什么区别？','route':'rewritten'}}}}]}]}
            return {'outputs':[{'outputs':[{'results':{'message':{'text':'教材回答'}}}]}]}
        job={'question':'它和MTTR有什么区别？','session_id':'test','retrieval_mode':'complete','history_json':json.dumps([{'question':'什么是MTBF？','answer':'平均故障间隔时间'}])}
        with patch.object(local,'call',side_effect=call):r=local.run_conversation(job)
        self.assertEqual(r['answer'],'教材回答')
        self.assertEqual(r['retrievalQuery'],'MTBF和MTTR有什么区别？')
        self.assertEqual(calls[1][0],'/run/session/'+CONVERSATION_FLOWS['complete'])
        value=calls[1][1]['input_request']
        self.assertEqual(value['input_value'],'MTBF和MTTR有什么区别？')
        self.assertEqual(value['tweaks']['ConversationAnswerContext-SysArch']['original_question'],job['question'])
    def test_no_history_followup_clarifies_without_retrieval(self):
        local=LocalFlow()
        with patch.object(local,'call') as call:r=local.run_conversation({'question':'它是什么？','history_json':'[]','session_id':'s'})
        call.assert_not_called();self.assertEqual(r['rewriteRoute'],'clarification')
    def test_inline_adm_target_reaches_answer_flow_without_rewrite(self):
        local=LocalFlow()
        question='结合教材 详细解释一下这个概念【ADM是架构开发方法（Architecture Development Method）】'
        with patch.object(local,'run_with_sources',return_value={'answer':'ADM教材回答','references':[]}) as run, patch.object(local,'call') as call:
            r=local.run_conversation({'question':question,'history_json':'[]','session_id':'s','retrieval_mode':'complete'})
        run.assert_called_once();call.assert_not_called()
        self.assertEqual(r['rewriteRoute'],'direct');self.assertEqual(r['retrievalQuery'],question)
        self.assertEqual(r['answer'],'ADM教材回答')
    def test_failed_rewrite_does_not_run_ambiguous_retrieval(self):
        local=LocalFlow()
        with patch.object(local,'call',side_effect=TimeoutError) as call:
            r=local.run_conversation({'question':'它是什么？','history_json':'[{"question":"MTBF","answer":"定义"}]','session_id':'s'})
        self.assertEqual(call.call_count,1);self.assertEqual(r['rewriteRoute'],'clarification')
if __name__=='__main__':unittest.main()
