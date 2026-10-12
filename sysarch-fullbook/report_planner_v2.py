"""Compare the frozen 20 questions; separate planning, retrieval and answers."""
import json
import re
import statistics
from pathlib import Path
from answer_citations import normalize_citations
from audit_planner_v2 import ROOT, difference_paths

EVAL = Path(r'F:\daily\output\sysarch-rag-evaluation')
BASELINE = EVAL/'planner-v1-citation-baseline-20261009'
CURRENT = EVAL/'planner-v2-final-20261009'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def source_metrics(rows, gold):
    if not gold:
        return None
    matches = {r['chunk_id'] for r in rows} & gold
    first = next((i for i, r in enumerate(rows, 1) if r['chunk_id'] in gold), None)
    return {'hit': bool(matches), 'coverage': len(matches)/len(gold), 'mrr': 1/first if first else 0}


def summarize(records):
    plans = [r['query_plan'] for r in records]
    relevant = [r['retrieval'] for r in records if r['retrieval'] is not None]
    return {'execution_ok': sum(r['status'] == 'ok' for r in records),
            'no_planner_call': sum(not p['planner_called'] for p in plans),
            'planner_calls': sum(bool(p['planner_called']) for p in plans),
            'accepted_plans': sum(p['planner_called'] and p['route'] == 'split' for p in plans),
            'fallbacks': sum(p['planner_called'] and p['route'] != 'split' for p in plans),
            'normalizations': sum(bool(p.get('normalizations')) for p in plans),
            'strict_pass': sum(r['scores'] == [2, 2, 2] for r in records),
            'called_questions_strict_pass': sum(r['scores'] == [2, 2, 2] for r in records if r['query_plan']['planner_called']),
            'no_call_questions_strict_pass': sum(r['scores'] == [2, 2, 2] for r in records if not r['query_plan']['planner_called']),
            'hit_questions': sum(m['hit'] for m in relevant),
            'reference_coverage': statistics.mean(m['coverage'] for m in relevant),
            'mrr': statistics.mean(m['mrr'] for m in relevant),
            'latency_mean': statistics.mean(r['elapsed_seconds'] for r in records),
            'latency_median': statistics.median(r['elapsed_seconds'] for r in records),
            'planning_mean_when_called': statistics.mean(p['planning_seconds'] for p in plans if p['planner_called']),
            'invalid_citation_ids': sum(len(r['citation_diagnostics']['invalid_ranks']) for r in records),
            'internal_marker_visible': sum(bool(re.search(r'</?think>|formula-not-decoded|\[公式占位\]', r['answer'], re.I)) for r in records)}


def main():
    dataset = load(EVAL/'dataset.json')
    assert load(BASELINE/'dataset-used.json') == load(CURRENT/'dataset-used.json') == dataset
    config_a, config_b = load(BASELINE/'configuration.json'), load(CURRENT/'configuration.json')
    for key in ('prompt', 'temperature', 'model', 'knowledge_base', 'top_k', 'dense_candidate_k', 'metadata_filter'):
        assert config_a[key] == config_b[key], key
    for nid in ('parser-h3mx9', 'FinalAnswerCleaner-SysArch', 'LanguageModelComponent-BpTTF', 'SubqueryPlannerModel-SysArch'):
        assert config_a['node_code_sha256'][nid] == config_b['node_code_sha256'][nid], nid
    # Baseline was built from a frozen copy. Only UI metadata drifted during execution.
    baseline_diff = load(ROOT/'activation.json')['baseline_nonfunctional_drift']
    assert all(p.startswith('/viewport/') or p.endswith('/selected') or p.endswith('/lf_version') for p in baseline_diff)
    assert all(s == 'ok' for s in load(CURRENT/'run-summary.json')['results'])
    reviews = {'baseline': load(ROOT/'baseline-review.json'), 'current': load(ROOT/'current-review.json')}
    records = {'baseline': [], 'current': []}
    detail = ['# 问题拆分优化：逐题对比', '',
              '同一20题各运行一次；评分由本助手对照同次context、必答要点和既有原页核对结果完成，未经独立人工标注。',
              '事实/完整/引用各0–2分；三项均2分才计严格通过。引用格式有效不等于内容支持该结论。', '']
    for test in dataset['tests']:
        qid = test['id']
        detail += [f'## {qid}', '', test['question'], '']
        for label, run in (('baseline', BASELINE), ('current', CURRENT)):
            q = load(run/(qid+'.json'))
            assert q['question'] == test['question'] and q['status'] == 'ok'
            plan, traces = q['query_plan'], q['retrieval_trace']['queries']
            assert len(plan['queries']) == len(traces) <= 3
            assert 1 <= len(q['retrieved_chunks']) <= 5
            for tr in traces:
                assert len(tr['dense_candidates']) <= 20 and len(tr['lexical_candidates']) <= 20
                for row in tr['dense_candidates'] + tr['lexical_candidates']:
                    assert row['section_type'] == 'body'
                    if tr['native_filter']:
                        assert row['chapter'] in tr['native_filter']['$and'][1]['chapter']['$in']
            review = reviews[label][qid]
            q['scores'], q['review_note'] = review['scores'], review['note']
            q['retrieval'] = source_metrics(q['retrieved_chunks'], {g['chunk_id'] for g in test['gold_sources']})
            q['citation_diagnostics'] = {k: v for k, v in normalize_citations(q['answer'], q['retrieved_chunks']).items() if k != 'text'}
            records[label].append(q)
            detail += [f'### {"旧拆分版本" if label == "baseline" else "优化版本"}', '',
                       f'评分 {review["scores"]}；总耗时 {q["elapsed_seconds"]}秒；计划路线 {plan["route"]}。', '',
                       review['note'], '', '```json', json.dumps(plan, ensure_ascii=False, indent=2), '```', '',
                       q['answer'], '', '| 片段 | 章节 | 教材页 | PDF页 |', '|---|---|---|---|']
            for rank, row in enumerate(q['retrieved_chunks'], 1):
                detail.append(f'| {rank} | {row.get("chapter")} | {row.get("book_pages")} | {row.get("pdf_pages")} |')
            detail += ['', f'[完整同次证据与候选记录]({run/(qid+".json")})', '']
    summaries = {label: summarize(rows) for label, rows in records.items()}
    changed = [{'id': a['id'], 'source_ids_same': [r['chunk_id'] for r in a['retrieved_chunks']] == [r['chunk_id'] for r in b['retrieved_chunks']],
                'before_scores': a['scores'], 'after_scores': b['scores'],
                'before_route': a['query_plan']['route'], 'after_route': b['query_plan']['route']}
               for a, b in zip(records['baseline'], records['current'])]
    output = {'summary': summaries, 'questions': changed, 'website_switched': False,
              'limitations': ['单轮模型生成与耗时存在随机波动，不能证明稳定收益',
                             '单次顺序运行及网络等待不是受控性能基准',
                             '参考分片集合非穷尽；词组/章节校验不能保证语义等价',
                             '基线flow_logic_unchanged为false仅因组件lf_version及UI变化；20题使用冻结代码配置']}
    (ROOT/'comparison.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'逐题对比.md').write_text('\n'.join(detail), encoding='utf-8')
    a, b = summaries['baseline'], summaries['current']
    lines = ['# 问题拆分可靠性优化结果', '',
             '独立流程：**教材检索与备考问答 · 问题拆分混合检索实验**。正式网页未切换。', '',
             '## 改动', '',
             '- 加强原句剪裁，不增加答案知识、英文翻译或章节。',
             '- 完整通用词组许可，转换措辞仅在用户原问题已有转化含义时许可。',
             '- 单章遗漏字段及已授权章节字符串可安全归一化；多章同章问题合并，仍覆盖所有指定章节。',
             '- 保存有限JSON搜索计划与回退原因；不保存原始思考文本，不增加模型重试。',
             '- 修正ASCII标识符边界：中文紧贴MTBF/MTTR时正常提取，原术语不可遗漏，中文紧贴新英文名也不能绕过校验。',
             '- 仅改计划节点和检索入口内的同版计划校验代码；实际检索、RRF、答案模型、引用处理与连线未变。', '',
             '## 同组20题实测', '', '| 指标 | 旧拆分版本 | 优化版本 |', '|---|---:|---:|',
             f'| 执行成功 | {a["execution_ok"]}/20 | {b["execution_ok"]}/20 |',
             f'| 未调用拆分模型 | {a["no_planner_call"]}题 | {b["no_planner_call"]}题 |',
             f'| 计划通过 / 拆分调用 | {a["accepted_plans"]}/{a["planner_calls"]} | {b["accepted_plans"]}/{b["planner_calls"]} |',
             f'| 回退次数 | {a["fallbacks"]} | {b["fallbacks"]} |',
             f'| 至少命中一个参考分片 | {a["hit_questions"]}/18 | {b["hit_questions"]}/18 |',
             f'| 平均参考分片ID覆盖 | {a["reference_coverage"]:.1%} | {b["reference_coverage"]:.1%} |',
             f'| MRR | {a["mrr"]:.4f} | {b["mrr"]:.4f} |',
             f'| 事实/完整/引用均满分 | {a["strict_pass"]}/20 | {b["strict_pass"]}/20 |',
             f'| 调用拆分的9题严格通过 | {a["called_questions_strict_pass"]}/9 | {b["called_questions_strict_pass"]}/9 |',
             f'| 未调用拆分的11题严格通过 | {a["no_call_questions_strict_pass"]}/11 | {b["no_call_questions_strict_pass"]}/11 |',
             f'| 本次平均整题耗时 | {a["latency_mean"]:.2f}秒 | {b["latency_mean"]:.2f}秒 |',
             f'| 拆分模型调用平均耗时 | {a["planning_mean_when_called"]:.2f}秒 | {b["planning_mean_when_called"]:.2f}秒 |', '',
             '## 每题路线与质量', '', '| 题号 | 旧路线 | 新路线 | 分片顺序相同 | 旧评分 | 新评分 |', '|---|---|---|---|---|---|']
    for q in changed:
        lines.append(f'| {q["id"]} | {q["before_route"]} | {q["after_route"]} | {q["source_ids_same"]} | {q["before_scores"]} | {q["after_scores"]} |')
    lines += ['', '## 仍需处理', '']
    for q in records['current']:
        if q['scores'] != [2, 2, 2]:
            lines.append(f'- {q["id"]}：{q["review_note"]}')
    for q in records['current']:
        if q['query_plan']['planner_called'] and q['query_plan']['route'] != 'split':
            lines.append(f'- {q["id"]}计划回退：{q["query_plan"].get("validation_error", q["query_plan"]["reason"])}。详见安全JSON计划。')
    lines += ['', '## 结论与使用', '',
              f'本轮完成校验缺陷修复，但本次最终对照没有证明整体收益：计划通过由{a["accepted_plans"]}/{a["planner_calls"]}变成{b["accepted_plans"]}/{b["planner_calls"]}，严格答案复核由{a["strict_pass"]}/20变成{b["strict_pass"]}/20。新增安全归一化在本轮实际计划中没有触发，只有对应单元测试验证。不能把单元测试通过、计划通过或引用格式有效等同于答案正确。', '',
              f'需要区分变化来源：调用拆分的9题严格通过{a["called_questions_strict_pass"]}→{b["called_questions_strict_pass"]}，未调用拆分的11题却{a["no_call_questions_strict_pass"]}→{b["no_call_questions_strict_pass"]}；后者不能归因于拆分逻辑，说明答案生成及单轮人工复核也存在波动。平均整题耗时同样未显示改善，本次不作稳定性能结论。', '',
              '保留独立实验，正式网页不切换。当前拒绝既有正确拦截的新英文名，也有“其/来”等保守误拒；不要为通过测试题不断放宽词库。下一步宜单独评估受约束的原句剪裁拆分，减少不必要改写；答案侧同时检查过强结论、证据缺项和辅助讲解是否越过来源。重排序或上线应等待对应评估支持。', '',
              '在Langflow打开上述实验，运行问题后查看“问题拆分与范围校验”输出：queries为实际计划，normalizations为格式修复，model_plan为有限JSON诊断，validation_error为回退原因。', '',
              '本次42项本地测试通过。保护验证确认正式流程和原混合实验代码/配置/连线未变；知识库完整行与正文快照、二进制向量索引未变。SQLite容器文件与前次保存哈希不同，因此不声称整个库目录字节不变。', '',
              '评分由本助手复核，非独立人工标注；参考ID集合不是唯一正确来源；单次20题不能代表全书准确率。两轮即使证据相同，模型输出也可能变化。单轮顺序耗时不是受控性能基准，不据此判断稳定性能改善。', '',
              f'[逐题计划、真实答案、证据及评分]({ROOT/"逐题对比.md"})',
              f'[保护验证]({ROOT/"verification.json"})', f'[回滚快照]({ROOT/"experiment-rollback.json"})']
    (ROOT/'优化结果.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(output['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
