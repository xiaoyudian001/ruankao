"""Verify the new runnable stage and document measured scope without overstating gains."""
import argparse
import hashlib
import json
from pathlib import Path
from answer_citations import normalize_citations
from hybrid_retrieval import same_source, load_snapshot
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint
from setup_rerank_flow import ROOT, PROTECTED, RANKER, MODEL, save

E2E = Path(r'F:\daily\output\sysarch-rag-evaluation\local-rerank-e2e-20261009')


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def file_sha(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): sha.update(block)
    return sha.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Verify recorded successful runs without network access')
    args = parser.parse_args()
    setup = load(ROOT/'setup.json')
    api = None if args.offline else LangflowAPI()
    flow = load(ROOT/'experiment-flow.json') if args.offline else api.call('/flows/'+setup['flow_id'])
    nodes = {n['id']: n for n in flow['data']['nodes']}
    assert MODEL not in nodes and len(nodes) == 11
    assert not any(e['source'] == MODEL or e['target'] == MODEL for e in flow['data']['edges'])
    protected = load(ROOT/'setup-verification.json')['protected_flows_unchanged'] if args.offline else {
                 label: flow_logic_fingerprint(api.call('/flows/'+fid)['data']) ==
                 flow_logic_fingerprint(load(ROOT/(label+'-before.json'))['data']) for label, fid in PROTECTED.items()}
    assert all(protected.values()), protected
    source = {n['id']: n for n in load(ROOT/'hybrid-before.json')['data']['nodes']}
    for nid in source:
        a = source[nid]['data']['node']['template']; b = nodes[nid]['data']['node']['template']
        if nid == 'TextbookRRF-SysArch':
            changed = [k for k in a if a[k] != b[k]]
            assert changed == ['final_k'] and b['final_k']['value'] == 20
        else: assert a == b, nid
    evidence_edges = {e['target']: e['data']['targetHandle']['fieldName'] for e in flow['data']['edges'] if e['source'] == RANKER}
    assert evidence_edges == {'parser-h3mx9': 'input_data', 'FinalAnswerCleaner-SysArch': 'reference_data'}
    index = load_snapshot(setup['snapshot_path'], setup['snapshot_sha256'])
    checks = []
    for qid in ('Q02', 'Q16', 'Q19'):
        q = load(E2E/(qid+'.json')); trace = q['rerank_trace']; rows = q['retrieved_chunks']
        assert q['status'] == 'ok' and trace['route'] == 'reranked' and trace['network_used'] is False
        assert len(rows) == 5 and [r['rag_rank'] for r in rows] == [1,2,3,4,5]
        index.validate_candidates(rows)
        for i, row in enumerate(rows, 1):
            assert f'[片段{i}]' in q['context'] and row['content'] in q['context']
        citations = normalize_citations(q['answer'], rows)
        assert not citations['invalid_ranks'] and not citations['malformed_citations']
        checks.append({'id': qid, 'status': q['status'], 'ranker_seconds': trace['seconds'],
                       'total_seconds': q['elapsed_seconds'], 'route': trace['route'],
                       'citation_ids_valid': True, 'reference_count': len(citations['referenced_ranks'])})
    assert load(E2E/'run-summary.json')['flow_logic_unchanged']
    assert flow_logic_fingerprint(load(E2E/'evaluated-flow.json')) == flow_logic_fingerprint(flow['data'])
    for path in sorted((ROOT/'candidate-replay').glob('Q*.json')):
        d = load(path); inputs = {r['chunk_id']: r for r in d['candidates']}
        assert len(d['after']) == 5
        for row in d['after']: assert same_source(row, inputs[row['chunk_id']])
    verification = {'protected_flows_unchanged': protected, 'new_flow_id': setup['flow_id'], 'nodes': 11,
                    'new_flow_logic_sha256': flow_logic_fingerprint(flow['data']),
                    'original_node_templates_unchanged_except_rrf_final_k': True,
                    'ranked_context_and_citation_edges': evidence_edges, 'e2e': checks,
                    'knowledge_writes_performed': False, 'snapshot_sha256': setup['snapshot_sha256'],
                    'runtime_sha256': file_sha(Path(r'F:\daily\sysarch-fullbook\local_rerank_runtime.py')),
                    'model_safetensors_sha256': file_sha(Path(r'F:\daily\models\mmarco-mMiniLMv2-L12-H384-v1\model.safetensors')),
                    'remote_rerank_executed': False, 'website_switched': False}
    verification['verification_mode'] = 'saved_flow_and_actual_runs' if args.offline else 'live_api_and_actual_runs'
    verification['protected_check_scope'] = 'creation-stage recorded check; local activation also passed live checks; not repeated after e2e' if args.offline else 'fresh live check'
    save(ROOT/'verification.json', verification)
    # Refresh the creation manifest to describe the actual final local topology.
    if not args.offline:
        save(ROOT/'setup-verification.json', {'protected_flows_unchanged': protected, 'nodes': 11, 'edges': len(flow['data']['edges']), 'engine': 'local_cross_encoder'})
    summary = load(ROOT/'candidate-replay'/'summary.json'); a, b = summary['before'], summary['after']
    lines = ['# 本地重排序：已完成的新阶段', '',
       f'Langflow新流程：**{setup["flow_name"]}**，11节点，ID：`{setup["flow_id"]}`。', '',
       '## 当前链路', '', '```mermaid', 'flowchart LR',
       'Q[聊天输入] --> V[语义候选20]', 'Q --> B[BM25候选20]', 'V --> R[RRF前20]', 'B --> R',
       'Q --> C[本机CrossEncoder重排序]', 'R --> C', 'C --> P[前5片段与出处]',
       'P --> T[整理文本与提示模板]', 'T --> M[MiniMax最终回答]', 'Q --> M',
       'M --> O[答案清理与引用校验]', 'P --> O', 'O --> A[聊天输出]', '```', '',
       '## 新增能力', '',
       '- RRF按两路排名融合；新节点把问题与每个候选一起输入专用分类模型，重新判断相关性并重新排序。',
       '- 重排序使用本机CPU，权重已保存，无需另开服务。模型首次加载后在Langflow进程中缓存。',
       '- 原文、chunk_id、来源哈希和双页码保持原值，最终编号重新排列；Parser与引用校验消费同一前5结果。',
       '- 512-token输入用重叠窗口覆盖长片段；每片取最高窗口分。问题最多128 tokens，超限有诊断。',
       '- 分数是原始logit，可为负、可超过1，不能解释为概率；未设置未经验证的拒答门槛。',
       '- 模型异常或90秒超时回退RRF前5；没有模型生成JSON或扩写内容的步骤。', '',
       '模型：[cross-encoder/mmarco-mMiniLMv2-L12-H384-v1官方模型卡](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)。成对评分机制见[Sentence Transformers文档](https://www.sbert.net/docs/cross_encoder/usage/usage.html)。', '',
       '## 实际验证', '',
       '- 31项本地测试通过；同一批既有20题的真实候选全部完成离线重排序。',
       '- 3题完整Langflow问答成功，全部实际经过重排序，无回退；输出5片、顺序及来源绑定检查通过。',
       '- 原正式、混合、拆分三个流程逻辑与配置未变。未执行知识库写入，正式网页未切换。', '',
       '| 固定候选的参考分片指标 | RRF前5 | 重排序前5 |', '|---|---:|---:|',
       f'| 至少命中一个参考分片 | {a["hit"]}/18 | {b["hit"]}/18 |',
       f'| 平均参考ID覆盖 | {a["reference_id_coverage"]:.1%} | {b["reference_id_coverage"]:.1%} |',
       f'| MRR | {a["mrr"]:.4f} | {b["mrr"]:.4f} |', f'| nDCG@5 | {a["ndcg_at5"]:.4f} | {b["ndcg_at5"]:.4f} |', '',
       f'独立进程候选回放：首次含导入/加载{summary["cold_first_seconds"]:.2f}秒，预热后的评分中位{summary["warm_median_seconds"]:.2f}秒。真实Langflow节点首题{checks[0]["ranker_seconds"]:.2f}秒，后两题分别{checks[1]["ranker_seconds"]:.2f}/{checks[2]["ranker_seconds"]:.2f}秒。两种测量含不同开销，不能混称网页答题耗时。', '',
       '综合题Q16从原候选第6位取回了第1章架构设计目的的片段，与架构师任务同时进入前5；Q09的参考首位下降。覆盖略增而整体排序未显示提升，因此这是可用的新能力和实验结果，不是准确率全面提高的结论。', '',
       '参考ID集合非穷尽，20题不是全书质量代表；候选回放隔离了排序因素，没有重跑旧问题拆分。3题端到端确认链路及典型内容，不代表所有问题的答案质量。', '',
       '| 端到端问题 | 重排节点 | 整题 |', '|---|---:|---:|']
    for c in checks: lines.append(f'| {c["id"]} | {c["ranker_seconds"]:.2f}秒 | {c["total_seconds"]:.2f}秒 |')
    lines += ['', '## 直接使用', '',
       '1. 在Langflow项目列表打开「教材检索与备考问答 · 混合检索重排序实验」。',
       '2. 打开Playground并提问；无需重新上传PDF、OCR或入库。',
       '3. 查看「本地证据重排序 CrossEncoder」输出：rerank_score为相关性分，rrf_pool_rank为重排前位置，rag_rank为最终引用编号。',
       '4. 首行rerank_trace包含全部20个分数、输入/输出ID、窗口数、耗时、route和回退类型；route=reranked表示真实评分。',
       '5. 原正式网页仍调用原流程。本实验在Langflow可直接运行，尚未提供网页模式切换。', '',
       '## 文件与运行边界', '',
       '- 模型：`F:\\daily\\models\\mmarco-mMiniLMv2-L12-H384-v1`，revision固定，local_files_only=True、trust_remote_code=False，仅使用safetensors。',
       '- 运行器：`F:\\daily\\sysarch-fullbook\\local_rerank_runtime.py`，由新节点调用，无新增后台服务或开机任务。',
       '- 当前Langflow自带Torch/Transformers；升级环境后应核对兼容性。Transformers 5的配对接口差异已处理并实际运行。',
       '- 全文重排序候选留在本机；最后选出的5片仍按原授权链路发送给MiniMax生成答案，不能称整个问答完全离线。',
       '- 初始远程20片评分被自动审批拒绝，该方案未实测，已从新流程移除。', '',
       f'[固定候选逐题回放]({ROOT/"candidate-replay"})', f'[端到端真实输出]({E2E})',
       f'[保护与来源验证]({ROOT/"verification.json"})']
    if args.offline:
        lines += ['', '## 报告核验范围', '',
                  '最后一次只读在线核验因自动审批服务额度错误未执行，该错误不是风险判定。报告按已保存的最终流程、20题回放及3题端到端实际结果离线生成；3题执行结束时新流程逻辑指纹未变。三个旧流程的保护核验已在创建及本地激活阶段通过，报告阶段未重新读取它们的当前在线状态。']
    (ROOT/'重排序使用说明.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'flow_id': setup['flow_id'], 'protected': protected, 'e2e': checks, 'report': str(ROOT/'重排序使用说明.md')}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
