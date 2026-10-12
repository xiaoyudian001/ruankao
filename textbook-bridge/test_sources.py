import unittest
from unittest.mock import patch
from bridge import answer_payload, LocalFlow


class SourceTransportTest(unittest.TestCase):
    def payload(self,refs):
        return {'outputs':[{'outputs':[{'results':{'message':{'text':'<think>private</think>答案',
            'session_metadata':{'textbook_refs':refs}}}}]}]}

    def test_actual_sources_survive_answer_cleaning(self):
        refs=[{'rank':2,'content':'本次检索片段'}]
        result=answer_payload(self.payload(refs))
        self.assertEqual(result,{'answer':'答案','references':refs})

    def test_independent_and_history_requests_both_return_snapshots(self):
        local=LocalFlow()
        for history in ['[]','[{"question":"MTBF的定义","answer":"平均故障间隔时间"}]']:
            with patch.object(local,'call',return_value=self.payload([{'rank':1}])):
                result=local.run_conversation({'question':'MTTR的定义','session_id':'s','history_json':history})
            self.assertEqual(result['references'],[{'rank':1}])

    def test_clarification_does_not_invent_sources(self):
        with patch.object(LocalFlow,'call') as call:
            result=LocalFlow().run_conversation({'question':'它是什么','session_id':'s','history_json':'[]'})
        call.assert_not_called();self.assertEqual(result['references'],[])


if __name__=='__main__':unittest.main()
