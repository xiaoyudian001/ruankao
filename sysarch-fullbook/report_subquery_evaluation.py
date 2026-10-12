"""Report frozen-set retrieval, plan execution, actual answers and manual reviews."""
import csv
import json
import math
import re
import statistics
from pathlib import Path

ROOT=Path(r'F:\daily\output\sysarch-rag-evaluation')
OUT=Path(r'F:\daily\output\sysarch-subquery-retrieval')
RUN=ROOT/'subquery-refined-20261009'
OLD=ROOT/'hybrid-verified-20261008'

def load(path):return json.loads(path.read_text(encoding='utf-8'))

def hit(rows,gold):
    ids={r['chunk_id'] for r in rows}
    matches=gold & ids
    first=next((i for i,r in enumerate(rows,1) if r['chunk_id'] in gold),None)
    return {'hit':bool(matches),'coverage':len(matches)/len(gold),'mrr':1/first if first else 0}

def main():
    dataset=load(ROOT/'dataset.json')
    assert load(RUN/'dataset-used.json')==dataset==load(OLD/'dataset-used.json')
    cfg,old_cfg=load(RUN/'configuration.json'),load(OLD/'configuration.json')
    for key in ('prompt','temperature','model','knowledge_base'):
        assert cfg[key]==old_cfg[key],key
    assert json.loads(cfg['metadata_filter'])==json.loads(old_cfg['metadata_filter'])
    assert cfg['top_k']==old_cfg['top_k']==5
    for nid in ('parser-h3mx9','FinalAnswerCleaner-SysArch','LanguageModelComponent-BpTTF'):
        assert cfg['node_code_sha256'][nid]==old_cfg['node_code_sha256'][nid],nid
    assert load(RUN/'run-summary.json')['flow_logic_unchanged']
    reviews=load(OUT/'answer-review.json')
    old_reviews={r['id']:r for r in load(OLD/'review.json')['questions']}
    records=[];times=[];detail=['# 问题拆分实验：逐题实际记录','',
        '固定20题单次顺序执行。评分为本助手对照同次context、既有参考要点与已核对原页的复核，非独立人工标注。答案保留原样。','']
    counts={'direct_no_model':0,'validated_split':0,'fallback':0,'model_calls':0}
    metrics={'previous':[],'current':[]}
    for t in dataset['tests']:
        qid=t['id'];q=load(RUN/(qid+'.json'));old=load(OLD/(qid+'.json'))
        assert q['question']==t['question'] and q['status']=='ok',qid
        assert 1<=len(q['retrieved_chunks'])<=5
        plan=q['query_plan'];traces=q['retrieval_trace']['queries']
        assert len(traces)==len(plan['queries'])<=3
        counts['model_calls']+=bool(plan['planner_called'])
        if not plan['planner_called']:counts['direct_no_model']+=1
        elif plan['route']=='split':counts['validated_split']+=1
        else:counts['fallback']+=1
        for tr in traces:
            assert len(tr['dense_candidates'])<=20 and len(tr['lexical_candidates'])<=20
            for c in tr['dense_candidates']+tr['lexical_candidates']:
                assert c['section_type']=='body'
                if tr['native_filter']:
                    assert c['chapter'] in tr['native_filter']['$and'][1]['chapter']['$in']
        gold={g['chunk_id'] for g in t['gold_sources']}
        current=hit(q['retrieved_chunks'],gold) if gold else None
        previous=hit(old['retrieved_chunks'],gold) if gold else None
        if gold:metrics['current'].append(current);metrics['previous'].append(previous)
        review=reviews[qid];scores=review['scores']
        record={'id':qid,'category':t['category'],'scores':scores,'strict_pass':scores==[2,2,2],
                'previous_strict_pass':old_reviews[qid]['strict_pass'],'review_note':review['note'],
                'route':plan['route'],'planner_called':plan['planner_called'],'subqueries':len(traces),
                'planning_seconds':plan['planning_seconds'],'elapsed_seconds':q['elapsed_seconds'],
                'previous_elapsed_seconds':old['elapsed_seconds'],'retrieval':current,'previous_retrieval':previous,
                'internal_marker_visible':bool(re.search(r'formula-not-decoded|\[公式占位\]|</?think>',q['answer'],re.I))}
        records.append(record);times.append(q['elapsed_seconds'])
        detail += [f'## {qid} · {t["category"]}','',t['question'],'',
            f'事实/完整/引用：{"/".join(map(str,scores))}；{q["elapsed_seconds"]}秒；路线{plan["route"]}。','',review['note'],'',
            '### 实际检索计划','', '```json',json.dumps(plan,ensure_ascii=False,indent=2),'```','',
            '### 模型实际答案','',q['answer'],'','### 最终证据','',
            '| 片段 | 章节 | 教材页 | PDF页 |','|---|---|---|---|']
        for i,c in enumerate(q['retrieved_chunks'],1):detail.append(f'| {i} | {c.get("chapter")} | {c.get("book_pages")} | {c.get("pdf_pages")} |')
        detail += ['',f'[原始问题、两路候选、RRF、context和答案]({RUN/(qid+".json")})','']
    retrieval={k:{'hit_questions':sum(x['hit'] for x in v),'answerable':len(v),
                  'mean_reference_coverage':round(statistics.mean(x['coverage'] for x in v),4),
                  'mrr':round(statistics.mean(x['mrr'] for x in v),4)} for k,v in metrics.items()}
    summary={'execution_ok':len(records),'strict_pass':sum(r['strict_pass'] for r in records),
             'previous_strict_pass':sum(r['previous_strict_pass'] for r in records),'retrieval':retrieval,
             'plan_routes':counts,'latency':{'mean':round(statistics.mean(times),2),'median':round(statistics.median(times),2),
                'p95':sorted(times)[math.ceil(.95*len(times))-1],'max':max(times),
                'previous_mean':round(statistics.mean(r['previous_elapsed_seconds'] for r in records),2)},
             'internal_marker_visible_count':sum(r['internal_marker_visible'] for r in records),'website_switched':False}
    (RUN/'review.json').write_text(json.dumps({'summary':summary,'questions':records},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'evaluation-details.md').write_text('\n'.join(detail),encoding='utf-8')
    with (OUT/'evaluation-scores.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['题号','事实','完整','引用','严格通过','原混合通过','路线','模型拆分调用','子问题数','拆分秒','整题秒','原整题秒','参考ID覆盖','原覆盖','备注'])
        for r in records:w.writerow([r['id'],*r['scores'],r['strict_pass'],r['previous_strict_pass'],r['route'],r['planner_called'],r['subqueries'],r['planning_seconds'],r['elapsed_seconds'],r['previous_elapsed_seconds'],(r['retrieval']or{}).get('coverage'),(r['previous_retrieval']or{}).get('coverage'),r['review_note']])
    q17=next(r for r in records if r['id']=='Q17')
    report=f'''# 问题拆分混合检索实验报告

## 已建立的流程

“教材检索与备考问答 · 问题拆分混合检索实验”，ID `730d9bd5-e084-4b32-814e-edea8d404c4b`。本轮未切换网页，源正式流程和源混合流程的参数、代码、连线未修改；原混合流程的画布信息和时间戳有变化，见保护验证。

## 固定20题结果

| 项目 | 原混合检索 | 本轮问题拆分实验 |
|---|---:|---:|
| 执行成功 | 20/20 | {summary['execution_ok']}/20 |
| 至少命中一个参考分片（18题有参考） | {retrieval['previous']['hit_questions']}/18 | {retrieval['current']['hit_questions']}/18 |
| 平均参考分片ID覆盖 | {retrieval['previous']['mean_reference_coverage']:.1%} | {retrieval['current']['mean_reference_coverage']:.1%} |
| 首个参考分片平均倒数排名（MRR，越高越好） | {retrieval['previous']['mrr']:.4f} | {retrieval['current']['mrr']:.4f} |
| 事实/完整/引用均满分 | {summary['previous_strict_pass']}/20 | {summary['strict_pass']}/20 |
| 单次整题平均耗时 | {summary['latency']['previous_mean']}秒 | {summary['latency']['mean']}秒 |

当前路线：{counts['direct_no_model']}题没有额外模型拆分调用；{counts['validated_split']}题使用校验通过的模型计划；{counts['fallback']}题调用拆分后回退。模型调用总数{counts['model_calls']}次。

Q17跨章题：参考ID覆盖从{q17['previous_retrieval']['coverage']:.1%}变为{q17['retrieval']['coverage']:.1%}；实际路线{q17['route']}，{q17['subqueries']}个检索问题，整题{q17['elapsed_seconds']}秒。回答复核：{q17['review_note']}

## 如何解释结果

同一固定问题、知识库、BM25快照、候选20、最终5片、Parser、答案模型温度0.2、提示词及答案清理；新加入计划模型温度0.1。新实现同时包含显式章节预过滤、逐子问题检索、均衡选片和后台复用，因此比较反映整套实验，不是仅对问题改写的消融证明。

参考ID并不是全书所有合法证据的全集，未命中某个参考ID不等于所有检索内容错误。命中也不等于回答正确。事实/完整/引用评分由本助手逐题审阅，未经过独立人工复核。

本轮耗时受模型响应和普通节点调度波动影响；只有一轮测试，不能证明长期速度。中位数{summary['latency']['median']}秒，P95 {summary['latency']['p95']}秒，最大{summary['latency']['max']}秒。拆分增加一次生成请求，遇到校验失败仍需支付该耗时；不应以本实验替换所有简单问题的直通策略。

## 限制与下一步

模型计划仍可能语义偏移，字符校验也会拒绝合理改写。计划与每路候选可检查；模型失败时原问题回退不会伪装成成功拆分。保留原公式补充与提示词不代表所有生成错误已解决。最终答案仍存在的具体问题见逐题详情。

跨章节找全证据的目标应与“所有答案完全可信”分别验收。网页正式调用暂未切换；对生成结论力度、引用完整范围和计划可靠性继续改进后，再做网页端比较与切换。

## 文件

- [学习说明](F:/daily/output/sysarch-subquery-retrieval/learning-guide.md)
- [20题实际计划、答案与审阅](F:/daily/output/sysarch-subquery-retrieval/evaluation-details.md)
- [评分CSV](F:/daily/output/sysarch-subquery-retrieval/evaluation-scores.csv)
- [原始测试记录](F:/daily/output/sysarch-rag-evaluation/subquery-refined-20261009/configuration.json)
- [原流程及知识库保护验证](F:/daily/output/sysarch-subquery-retrieval/final-verification.json)

首次试跑的错误是Langflow将诊断JSON长字符串截断，评测脚本不能解码；实际流程到达聊天输出。这些试跑不参与本表。修复为结构化诊断字段后，最终固定20题完整执行，保留配置哈希与实际结果供核查。
'''
    (OUT/'experiment-report.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
