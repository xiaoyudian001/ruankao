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
 def test_tagged_case_feedback_preserves_quotes_and_newlines(self):
  from critique import parse_result
  raw='<critique><summary>核对 "业务条件"\n按本问判断</summary><correct><point><text>已说明通用结构</text><ranks>[2]</ranks></point></correct><missing></missing><corrections></corrections><suggestion>可以进一步对比，但非必需。</suggestion><insufficient_evidence>false</insufficient_evidence></critique>'
  result=parse_result(raw,[2]);self.assertIn('"业务条件"\n',result['summary']);self.assertEqual(result['missing'],[]);self.assertEqual(result['correct'][0]['ranks'],[2])
  with self.assertRaises(ValueError):parse_result(raw,[1])
 def test_tag_order_and_empty_self_closing_containers_are_equivalent(self):
  from critique import parse_result
  raw='<critique><insufficient_evidence>false</insufficient_evidence><suggestion>补充当前小问即可。</suggestion><summary>核心要点已覆盖。</summary><correct/><corrections /><missing></missing></critique>'
  result=parse_result(raw,[1]);self.assertEqual(result['summary'],'核心要点已覆盖。');self.assertEqual(result['missing'],[])
  with self.assertRaises(ValueError):parse_result(raw.replace('<summary>核心要点已覆盖。</summary>',''),[1])
 def test_consecutive_explicit_rank_arrays_are_normalized_without_inventing_sources(self):
  from critique import parse_result
  raw='<critique><summary>已覆盖</summary><correct><point><text>通用结构与差异适配</text><ranks>[1], [2]</ranks></point></correct><missing/><corrections/><suggestion>继续练习</suggestion><insufficient_evidence>false</insufficient_evidence></critique>'
  result=parse_result(raw,[1,2]);self.assertEqual(result['correct'][0]['ranks'],[1,2])
  with self.assertRaises(ValueError):parse_result(raw,[1])
if __name__=='__main__':unittest.main()
