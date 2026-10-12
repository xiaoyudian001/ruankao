import json,unittest
class CritiqueContract(unittest.TestCase):
 def test_extracts_custom_component_message(self):
  from critique import critique_text
  response={'outputs':[{'outputs':[{'outputs':{'critique':{'message':{'text':'{"summary":"中文"}'}}}}]}]}
  self.assertEqual(critique_text(response),'{"summary":"中文"}')
 def test_payload_survives_installed_langflow_unescaping(self):
  from critique import encode_payload,decode_payload
  from test_conversation_bridge import langflow_string
  job={'front':'MTBF "定义"','back':'内容\nC:\\notes\\new','response':'我说\tMTTR\\n','references_json':'[{"rank":1,"content":"引号 \\"x\\""}]'}
  self.assertEqual(decode_payload(langflow_string(encode_payload(job))),job)
 def test_json_roundtrip_and_source_priority(self):
  from critique import build_prompt
  response='我的答案 "MTBF"\nC:\\笔记\\章节'
  prompt=build_prompt({'front':'定义MTBF','back':'可编辑参考','response':response,'references_json':json.dumps([{'rank':2,'content':'平均故障间隔时间','label':'教材308页'}],ensure_ascii=False)})
  self.assertEqual(json.loads(prompt['data'])['response'],response)
  self.assertIn('教材片段',prompt['system']);self.assertIn('事实依据',prompt['system'])
 def test_model_json_validation(self):
  from critique import parse_result
  sample={'summary':'摘要','correct':[{'point':'正确','ranks':[2]}],'missing':[],'corrections':[],'suggestion':'再复习','insufficientEvidence':False}
  self.assertEqual(parse_result('<think>hidden</think>'+json.dumps(sample),[2]),sample)
  with self.assertRaises(ValueError):parse_result(json.dumps(sample),[1])
  with self.assertRaises(ValueError):parse_result('invalid output',[2])
if __name__=='__main__':unittest.main()
