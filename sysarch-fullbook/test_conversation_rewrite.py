import json, unittest
from conversation_rewrite import prepare_rewrite, validate_rewrite, answer_context, bounded_history, encode_history

class ConversationTest(unittest.TestCase):
    history=[{'question':'什么是MTBF？','answer':'MTBF是平均故障间隔时间。教材第308页。'}]
    def test_transport_keeps_legacy_valid_json_and_bounds(self):
        raw=[{'question':'中文问题'*600,'answer':'<think>隐藏内容</think>\n'+'中文答案'*400} for _ in range(5)]
        expected=bounded_history(raw)
        self.assertEqual(len(expected),3)
        self.assertEqual(len(expected[0]['question']),2000)
        self.assertEqual(len(expected[0]['answer']),1000)
        self.assertEqual(bounded_history(encode_history(raw)),expected)
        self.assertEqual(bounded_history(json.dumps(raw,ensure_ascii=False)),expected)
        self.assertEqual(bounded_history(encode_history([])),[])
    def test_transport_rejects_invalid_encoding_json_and_schema(self):
        import base64
        for value in ('history-b64-v1:@@@','history-b64-v1:'+base64.b64encode(b'\xff').decode(),
                      'history-b64-v1:'+('A'*65536)):
            with self.subTest(value=value[:40]):self.assertRaises(ValueError,bounded_history,value)
        for raw in ('not-json','{}','[{"question":"q","answer":42}]','[{"question":"q","answer":"bad\njson"}]'):
            encoded='history-b64-v1:'+base64.b64encode(raw.encode()).decode()
            with self.subTest(raw=raw):self.assertRaises(ValueError,bounded_history,encoded)
        self.assertRaises(ValueError,bounded_history,'[{"question":"q","answer":"bad\njson"}]')
    def test_independent_question_ignores_old_topic(self):
        self.assertEqual(prepare_rewrite('什么是软件架构？',self.history)['route'],'direct')
        self.assertEqual(prepare_rewrite('什么是软件架构？请举个例子。',[])['route'],'direct')
        self.assertEqual(prepare_rewrite('其他架构风格有哪些？',self.history)['route'],'direct')
        self.assertEqual(prepare_rewrite('再举个例子',self.history)['route'],'pending')
    def test_first_turn_pronoun_requires_clarification(self):
        self.assertEqual(prepare_rewrite('它和MTTR有什么区别？',[])['route'],'clarification')
    def test_explicit_inline_concept_does_not_require_history(self):
        question='结合教材 详细解释一下这个概念【ADM是架构开发方法（Architecture Development Method）】'
        for history in ([],self.history):
            p=prepare_rewrite(question,history)
            self.assertEqual(p['route'],'direct')
            self.assertEqual(p['query'],question)
        for q in ('详细解释这个概念【软件架构】', '介绍这种方法：[ADM]', '解释该方法`ADM`'):
            self.assertEqual(prepare_rewrite(q,[])['route'],'direct')
    def test_inline_label_does_not_hide_other_ambiguous_references(self):
        for q in ('这个概念【上面那个】是什么？','这个概念【请详细解释】是什么？',
                  '这个概念【第2章】是什么？','这个概念【ADM】和它有什么区别？'):
            self.assertEqual(prepare_rewrite(q,[])['route'],'clarification')
        self.assertEqual(prepare_rewrite('这个概念是什么？',self.history)['route'],'pending')
    def test_validation_accepts_resolved_inline_label(self):
        p=prepare_rewrite('它和ADM有什么区别？',self.history)
        query='MTBF和这个概念【ADM】有什么区别？'
        self.assertEqual(validate_rewrite(p,json.dumps({'query':query,'needs_clarification':False}))['route'],'rewritten')
    def test_followup_uses_bounded_same_session_context(self):
        p=prepare_rewrite('它和MTTR有什么区别？',self.history)
        self.assertEqual(p['route'],'pending')
        self.assertEqual(p['history_count'],1)
        r=validate_rewrite(p,json.dumps({'query':'MTBF和MTTR有什么区别？','needs_clarification':False}))
        self.assertEqual(r['route'],'rewritten')
        self.assertIn('MTBF',r['query'])
    def test_cannot_remove_explicit_terms_or_add_new_terms(self):
        p=prepare_rewrite('它和MTTR有什么区别？',self.history)
        for query in ('MTBF是什么？','MTBF与HTTP有什么区别？','MTBF在第99章的定义是什么？'):
            self.assertRaises(ValueError,validate_rewrite,p,json.dumps({'query':query,'needs_clarification':False}))
    def test_current_chapter_overrides_history(self):
        p=prepare_rewrite('第9章中它的定义是什么？',[{'question':'第17章的MTBF是什么？','answer':'MTBF'}])
        self.assertRaises(ValueError,validate_rewrite,p,json.dumps({'query':'第17章的MTBF是什么？','needs_clarification':False}))
    def test_current_requested_aspect_is_preserved(self):
        p=prepare_rewrite('它的缺点是什么？',[{'question':'事件驱动架构是什么？','answer':'定义'}])
        self.assertRaises(ValueError,validate_rewrite,p,json.dumps({'query':'事件驱动架构的优点是什么？','needs_clarification':False}))
    def test_invalid_or_ambiguous_output_does_not_search(self):
        p=prepare_rewrite('它是什么？',self.history)
        r=validate_rewrite(p,'{"query":"","needs_clarification":true}')
        self.assertEqual(r['route'],'clarification')
        self.assertRaises(ValueError,validate_rewrite,p,'not json')
    def test_answer_context_keeps_original_and_labels_history(self):
        text=answer_context('它和MTTR有什么区别？','MTBF和MTTR有什么区别？',self.history)
        self.assertIn('用户原问题',text)
        self.assertIn('不作为教材事实或引用依据',text)
        self.assertIn('MTBF和MTTR',text)

if __name__=='__main__': unittest.main()
