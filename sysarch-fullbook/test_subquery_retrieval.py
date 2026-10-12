import unittest
try:
    import subquery_retrieval as s
except ImportError:
    s = None

def row(cid, chapter='第9章软件可靠性', pages='323'):
    return dict(chunk_id=cid, content='正文'+cid, chapter=chapter, section_type='body',
                source_sha256='hash', pdf_pages=pages, book_pages='308', rrf_score=.03)

class SubqueryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(s, '缺少问题拆分检索实现')

    def test_simple_original_query_no_model(self):
        self.assertFalse(s.needs_split('MTTR 是什么意思？'))
        self.assertEqual(s.fallback_plan('MTTR 是什么意思？')['queries'], [{'query':'MTTR 是什么意思？','chapter':None}])

    def test_chinese_chapters_and_cross_chapter_route(self):
        q='结合第九章MTTR定义与第十七章高可用设计说明降低MTTR'
        self.assertEqual(s.explicit_chapters(q), [9,17])
        self.assertTrue(s.needs_split(q))
        self.assertEqual([r['chapter'] for r in s.fallback_plan(q,'timeout')['queries']], [9,17])

    def test_parse_valid_json_and_remove_think(self):
        q='结合第9章定义与第17章应用说明MTTR'
        p=s.parse_plan(q, '<think>private</think>```json\n{"queries":[{"query":"MTTR定义","chapter":9},{"query":"MTTR应用","chapter":17}]}\n```')
        self.assertEqual(p['route'],'split')
        self.assertEqual(len(p['queries']),2)
        self.assertNotIn('private',str(p))

    def test_unrequested_scope_and_incomplete_scope_rejected(self):
        for raw in ('{"queries":[{"query":"x","chapter":9},{"query":"y","chapter":18}]}',
                    '{"queries":[{"query":"x","chapter":9},{"query":"y","chapter":9}]}'):
            with self.assertRaises(ValueError):s.parse_plan('比较第9章和第17章MTTR',raw)
        with self.assertRaises(ValueError):s.parse_plan('比较外模式与内模式','{"queries":[{"query":"外模式","chapter":6},{"query":"内模式","chapter":6}]}')

    def test_query_count_duplicates_and_shape_rejected(self):
        for obj in ({'queries':[{'query':'x','chapter':None}]},
                    {'queries':[{'query':'x','chapter':None}]*2},
                    {'queries':[{'query':str(i),'chapter':None} for i in range(4)]},
                    {'queries':[{'query':'x','chapter':None},{'query':'','chapter':None}]}):
            import json
            with self.assertRaises(ValueError):s.parse_plan('比较A和B',json.dumps(obj))

    def test_balanced_evidence_prevents_chapter_starvation(self):
        a=[row(str(i)) for i in range(5)]
        b=[row('b','第17章网络', '628')]
        out=s.merge_evidence([{'query':'定义','chapter':9},{'query':'应用','chapter':17}],[a,b],5)
        self.assertIn('b',[r['chunk_id'] for r in out])
        self.assertEqual(len(out),5)
        self.assertEqual(next(r for r in out if r['chunk_id']=='b')['pdf_pages'],'628')

    def test_same_chunk_dedup_and_all_query_labels_preserved(self):
        out=s.merge_evidence([{'query':'A','chapter':None},{'query':'B','chapter':None}],
                             [[row('same'),row('a')],[row('same'),row('b')]],5)
        self.assertEqual(len(out),3)
        self.assertEqual(out[0]['matched_queries'],['A','B'])
        bad=row('same');bad['content']='changed'
        with self.assertRaises(ValueError):s.merge_evidence([{'query':'A'},{'query':'B'}],[[row('same')],[bad]],5)

    def test_chapter_filter_only_matches_actual_metadata(self):
        rows=[row('a'),row('b','第17章网络','628')]
        self.assertEqual(s.chapter_filter(rows,9), {'$and':[{'section_type':'body'},{'chapter':{'$in':['第9章软件可靠性']}}]})
        with self.assertRaises(ValueError):s.chapter_filter(rows,88)

    def test_multi_aspect_question_routes_to_split(self):
        self.assertTrue(s.needs_split('MTBF和MTTR的公式是什么？为什么不能一直提高MTBF？哪些因素也影响可用性？'))

    def test_planner_does_not_inject_new_answer_concepts(self):
        with self.assertRaises(ValueError):
            s.parse_plan('比较第9章和第17章MTTR', '{"queries":[{"query":"第9章MTTR定义","chapter":9},{"query":"第17章MTTR冗余设计","chapter":17}]}')

    def test_generic_question_words_are_not_new_concepts(self):
        p=s.parse_plan('数据库外模式与内模式有什么不同？从面向对象和描述内容两个方面比较。',
            '{"queries":[{"query":"数据库外模式各自关注的描述内容","chapter":null},{"query":"数据库内模式区别和职责","chapter":null}]}')
        self.assertEqual(p['route'],'split')

    def test_new_english_product_name_is_not_allowed(self):
        with self.assertRaises(ValueError):s.parse_plan('比较外模式与内模式',
            '{"queries":[{"query":"外模式 Kafka","chapter":null},{"query":"内模式","chapter":null}]}')

    def test_evaluation_fingerprint_ignores_canvas_but_detects_logic(self):
        import copy
        import run_rag_evaluation as runner
        original={'viewport':{'x':1},'nodes':[{'id':'n','position':{'x':1},'data':{'node':{'last_updated':'a','template':{'temperature':{'value':.2}}}}}],'edges':[]}
        changed=copy.deepcopy(original);changed['viewport']['x']=100;changed['nodes'][0]['data']['node']['last_updated']='b'
        self.assertEqual(runner.flow_logic_fingerprint(original),runner.flow_logic_fingerprint(changed))
        changed['nodes'][0]['data']['node']['template']['temperature']['value']=.8
        self.assertNotEqual(runner.flow_logic_fingerprint(original),runner.flow_logic_fingerprint(changed))

    def test_complete_generic_phrases_do_not_allow_new_topics(self):
        import json
        q='数据库外模式与内模式有什么不同？从面向对象和描述内容两个方面比较。'
        result=s.parse_plan(q,json.dumps({'queries':[{'query':'外模式从什么视角描述内容','chapter':None},{'query':'内模式的面向对象和描述内容','chapter':None}]}))
        self.assertEqual(result['route'],'split')
        with self.assertRaises(ValueError):s.parse_plan(q,json.dumps({'queries':[{'query':'外模式视图安全','chapter':None},{'query':'内模式','chapter':None}]}))

    def test_transform_word_permission_depends_on_original(self):
        raw='{"queries":[{"query":"架构设计的目的是什么","chapter":null},{"query":"架构师将需求转换成系统的任务","chapter":null}]}'
        self.assertEqual(s.parse_plan('结合架构设计的目的和架构师的任务，说明如何把需求转成系统。',raw)['route'],'split')
        with self.assertRaises(ValueError):s.parse_plan('架构设计的目的和架构师的任务是什么？',raw)

    def test_single_explicit_chapter_safe_format_repair(self):
        p=s.parse_plan('依据第9章比较MTTF与MTTR',
          '{"queries":[{"query":"MTTF定义","chapter":"第九章"},{"query":"MTTR定义"}]}')
        self.assertEqual([q['chapter'] for q in p['queries']],[9,9])
        self.assertTrue(p['normalizations'])
        for chapter in ['17','true','9.0']:
            with self.assertRaises(ValueError):s.parse_plan('依据第9章比较MTTF与MTTR',
                '{"queries":[{"query":"MTTF定义","chapter":'+chapter+'},{"query":"MTTR定义","chapter":9}]}')

    def test_same_chapter_queries_merge_without_dropping_scope(self):
        q='结合第9章MTTR定义与第17章网络高可用设计，说明降低MTTR为何有效，以及可从哪两个方向着手。'
        p=s.parse_plan(q,'{"queries":[{"query":"MTTR定义","chapter":"9"},{"query":"网络高可用设计","chapter":17},{"query":"降低MTTR的两个方向","chapter":17}]}')
        self.assertEqual([x['chapter'] for x in p['queries']],[9,17])
        self.assertIn('网络高可用设计',p['queries'][1]['query'])
        self.assertIn('降低MTTR',p['queries'][1]['query'])
        with self.assertRaises(ValueError):s.parse_plan(q,
            '{"queries":[{"query":"MTTR定义","chapter":9},{"query":"降低MTTR的两个方向","chapter":9}]}')

    def test_more_factors_question_can_use_generic_followup(self):
        p=s.parse_plan('MTBF和MTTR有什么网络可用性公式？哪些系统因素也影响网络高可用性？',
           '{"queries":[{"query":"MTBF和MTTR的网络可用性公式","chapter":null},{"query":"除此之外还有哪些系统因素影响网络高可用性","chapter":null}]}')
        self.assertEqual(p['route'],'split')

    def test_safe_model_plan_diagnostic_never_contains_think(self):
        p=s.decode_plan('<think secret="yes">private text</think>```json\n{"queries":[]}\n```')
        self.assertEqual(p,{'queries':[]})

    def test_existing_english_terms_adjacent_to_chinese_are_preserved(self):
        q='教材用MTBF和MTTR给出了什么网络可用性公式？哪些因素影响网络高可用性？'
        p=s.parse_plan(q,'{"queries":[{"query":"MTBF MTTR 网络可用性公式是什么","chapter":null},{"query":"哪些因素影响网络高可用性","chapter":null}]}')
        self.assertEqual(p['route'],'split')

    def test_chinese_adjacent_acronym_cannot_be_dropped(self):
        with self.assertRaises(ValueError):s.parse_plan('比较MTTF与MTTR的定义',
            '{"queries":[{"query":"MTTF定义","chapter":null},{"query":"定义的含义","chapter":null}]}')

    def test_new_english_name_adjacent_to_chinese_is_rejected(self):
        with self.assertRaises(ValueError):s.parse_plan('比较外模式与内模式',
            '{"queries":[{"query":"外模式Kafka内容","chapter":null},{"query":"内模式","chapter":null}]}')

if __name__=='__main__':unittest.main()
