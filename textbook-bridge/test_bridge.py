import importlib.util, unittest
from pathlib import Path

class BridgeTest(unittest.TestCase):
    def test_mode_whitelist_and_default_compatibility(self):
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('bridge.py'))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertEqual(m.flow_for_mode(None),m.FLOW)
        self.assertEqual(m.flow_for_mode('default'),m.FLOW)
        self.assertEqual(m.flow_for_mode('complete'),'ce82698e-54b8-4360-8a11-6f6c4f43f5ff')
        for mode in ('other','http://evil','2e38f267-52d8-484f-bc4a-81ad7a2e3436'):
            self.assertRaises(ValueError,m.flow_for_mode,mode)
        local=m.LocalFlow()
        calls=[]
        def call(path,body=None,timeout=20,**kwargs):
            calls.append((path,body,timeout))
            return {'outputs':[{'outputs':[{'results':{'message':{'text':'最终答案'}}}]}]}
        with patch.object(local,'call',side_effect=call):
            local.run({'question':'测试','session_id':'session','retrieval_mode':'complete'})
        self.assertEqual(calls[0][0],'/run/session/'+m.flow_for_mode('complete'))
        self.assertNotIn('retrieval_mode',calls[0][1]['input_request']['tweaks'])

    def test_only_final_chat_output_and_strip_think(self):
        path=Path(__file__).with_name('bridge.py')
        self.assertTrue(path.exists(),'本地问答连接尚未实现')
        spec=importlib.util.spec_from_file_location('bridge',path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        result={'outputs':[{'outputs':[{'results':{'message':{'text':'<think>hidden</think>MTBF 教材第308页（PDF第323页）'}}}]}]}
        self.assertEqual(m.answer_text(result),'MTBF 教材第308页（PDF第323页）')
        self.assertEqual(m.clean_answer('答案<think>unfinished'),'答案')
        self.assertRaises(ValueError,m.answer_text,{'outputs':[]})
        self.assertRaises(ValueError,m.answer_text,{'outputs':[{'outputs':[{'results':{'message':{'text':'<think>only</think>'}}}]}]})

    def test_connector_identifies_itself(self):
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('bridge.py'))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return b'{}'
        with patch.object(m,'urlopen',return_value=Response()) as call:
            m.request_json('https://example.com',{'action':'heartbeat'})
            self.assertEqual(call.call_args.args[0].get_header('User-agent'),'TextbookConnector/1.0')

if __name__=='__main__':unittest.main()
