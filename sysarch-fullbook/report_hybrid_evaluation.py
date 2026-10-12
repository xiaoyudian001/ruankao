"""Report same-question hybrid retrieval and explicit answer review separately."""
import csv
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(r"F:\daily\output\sysarch-rag-evaluation")
RUN = ROOT / "hybrid-verified-20261008"
OUT = Path(r"F:\daily\output\sysarch-hybrid-retrieval")
REVIEWS = {
    "Q01": ([2, 1, 2], "引用内容真实，但仍以信息系统架构等其他语境回答一般定义，未覆盖第1章组件、连接件、约束及演化原理。目标片段在语义候选第11名，未进融合前5。"),
    "Q02": ([2, 2, 2], "第1章五项作用齐全，并明确区分第7章另一组列表。"),
    "Q03": ([2, 2, 2], "四层和职责完整，来源范围正确。"),
    "Q04": ([2, 2, 2], "四部分作用及简单项目可合并的条件完整。"),
    "Q05": ([2, 2, 2], "内核/插件职责和减少通信而非禁止通信均正确；第18章补充有直接出处，主板协调放在明确标注的类比中，没有再保证插件替换不影响其他插件。"),
    "Q06": ([2, 2, 2], "四种模型完整准确，说明它们可以有机结合。"),
    "Q07": ([2, 2, 2], "三级模式、职责、描述内容及映像关系正确；引用页范围完整。"),
    "Q08": ([2, 2, 2], "MTTF积分和不可修复系统含义正确，多页引用这次完整。"),
    "Q09": ([1, 2, 1], "第9章主定义及三项组成正确，但辅助段把第9章与第17章说成同一个A公式的同一角色，片段未支持这种跨章等同；还有片段3引用格式错误。"),
    "Q10": ([2, 2, 2], "可发现性、注册中心推送及扩展能力直接来自第14章片段，未再补无依据的实现机制。"),
    "Q11": ([2, 2, 2], "描述重点和结构模型研究核心正确，框架模型核心明确记为教材未提及。"),
    "Q12": ([1, 2, 1], "完整动态模型证据进入最终第2条，但回答仍增加运行时限定、预定义开发顺序和独立刻画等教材未明确列出的对比项。"),
    "Q13": ([2, 2, 2], "外模式/内模式对象及内容正确，使用单页支持来源，未再缩写多页引用。"),
    "Q14": ([1, 2, 1], "主公式和指数分布条件正确，但把MTTF主要限定于不可修复系统；辅助段把MTBF说成故障结束到下次故障发生，同时用含修复时间的周期求和，时间起点和组成不一致。"),
    "Q15": ([2, 2, 2], "架构师技术领导与项目经理资源、进度、成本对比正确，有直接出处。"),
    "Q16": ([2, 2, 2], "此前缺失的教材第15～16页完整任务段落进入融合第3条；回答包含技术协调、推动决策、文档化多视图，并用第7章目的作有效支持。后文转化步骤编号应与原文任务编号区分，但未遗漏核心要求。"),
    "Q17": ([1, 1, 1], "两路20候选均无第9章目标片段，仍缺跨章证据；回答说明不足合理，但主段增加了更可控、更现实的比较力度。"),
    "Q18": ([1, 1, 1], "网络公式及实际计算局限正确；仍把有效途径加强成还需要配合，主要依据未覆盖协议；片段1多处由613～614/PDF628～629缩为单页。"),
    "Q19": ([2, 2, 1], "未编造虚构设备端口，但说明中片段1引用由603～604/PDF618～619缩成单页，按完整source_hint规则扣引用分。拒绝行为单独算通过。"),
    "Q20": ([2, 2, 2], "未编造虚构框架重试次数或出处。"),
}


def retrieval_metrics(rows, gold):
    hits = gold & {r["chunk_id"] for r in rows}
    first = next((i for i, r in enumerate(rows, 1) if r["chunk_id"] in gold), None)
    return {"hit": bool(hits), "coverage": len(hits) / len(gold), "reciprocal_rank": 1 / first if first else 0}


def main():
    dataset = json.loads((ROOT / "dataset.json").read_text(encoding="utf-8"))
    assert dataset == json.loads((RUN / "dataset-used.json").read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "formula-fix-20261008" / "review.json").read_text(encoding="utf-8"))
    old_reviews = {q["id"]: q for q in baseline["questions"]}
    old_cfg = json.loads((ROOT / "formula-fix-20261008" / "configuration.json").read_text(encoding="utf-8"))
    cfg = json.loads((RUN / "configuration.json").read_text(encoding="utf-8"))
    for key in ("prompt", "temperature", "model", "knowledge_base", "metadata_filter"):
        assert old_cfg[key] == cfg[key], "Comparison configuration differs: " + key
    for nid in ("parser-h3mx9", "FinalAnswerCleaner-SysArch", "LanguageModelComponent-BpTTF"):
        assert old_cfg["node_code_sha256"][nid] == cfg["node_code_sha256"][nid]
    assert json.loads((RUN / "run-summary.json").read_text(encoding="utf-8"))["flow_unchanged"]
    records, route_metrics, times = [], {}, []
    detail = ["# 混合检索20题：实际答案与两路候选", "",
              "模型输出保持原样；评分由本助手对照测试要点、同次context和已核对原页完成，未经独立人工复核。", ""]
    for t in dataset["tests"]:
        qid = t["id"]
        saved = json.loads((RUN / (qid + ".json")).read_text(encoding="utf-8"))
        old = json.loads((ROOT / "formula-fix-20261008" / (qid + ".json")).read_text(encoding="utf-8"))
        assert saved["question"] == t["question"] and saved["status"] == "ok"
        assert len(saved["retrieved_chunks"]) == 5
        assert len(saved["dense_candidates"]) == 20
        gold = {s["chunk_id"] for s in t["gold_sources"]}
        routes = {"previous_dense5": old["retrieved_chunks"][:5], "same_run_dense5": saved["dense_candidates"][:5],
                  "bm25_5": saved["lexical_candidates"][:5], "fused5": saved["retrieved_chunks"],
                  "dense20": saved["dense_candidates"], "bm25_20": saved["lexical_candidates"]}
        metrics = {}
        if gold:
            for key, rows in routes.items():
                metrics[key] = retrieval_metrics(rows, gold)
                route_metrics.setdefault(key, []).append(metrics[key])
        scores, note = REVIEWS[qid]
        record = {"id": qid, "category": t["category"], "status": saved["status"],
                  "scores": dict(zip(["factual", "completeness", "citation"], scores)),
                  "strict_pass": scores == [2, 2, 2], "baseline_strict_pass": old_reviews[qid]["strict_pass"],
                  "baseline_scores": old_reviews[qid]["scores"], "review_note": note,
                  "elapsed_seconds": saved["elapsed_seconds"], "retrieval_metrics": metrics,
                  "no_answer_refusal_pass": qid in ("Q19", "Q20"),
                  "internal_marker_visible": bool(re.search(r"formula-not-decoded|\[公式占位\]|</?think>", saved["answer"], re.I))}
        records.append(record)
        times.append(saved["elapsed_seconds"])
        detail += [f"## {qid} · {t['category']}", "", t["question"], "",
                   f"评分事实/完整/引用：{'/'.join(map(str, scores))}；{saved['elapsed_seconds']}秒。", "", note,
                   "", "### 参考要点", ""]
        detail += ["- " + p for p in t["required_points"]]
        detail += ["", "### 模型实际答案", "", saved["answer"], "", "### 最终5片段", "",
                   "| 片段 | 教材页 | PDF页 | 语义排名 | 关键词排名 | RRF分数 |", "|---|---|---|---|---|---|"]
        for i, c in enumerate(saved["retrieved_chunks"], 1):
            detail.append(f"| {i} | {c.get('book_pages', '')} | {c.get('pdf_pages', '')} | {c.get('dense_rank')} | {c.get('lexical_rank')} | {c['rrf_score']:.6f} |")
        detail += ["", f"[同次20＋20候选、context与答案]({RUN / (qid + '.json')})", ""]
    retrieval = {key: {"hit_questions": sum(v["hit"] for v in values), "answerable_questions": len(values),
                       "mean_reference_coverage": round(statistics.mean(v["coverage"] for v in values), 4),
                       "mrr": round(statistics.mean(v["reciprocal_rank"] for v in values), 4)}
                 for key, values in route_metrics.items()}
    node_means = {}
    for nid in ("Knowledge-Y8gm2", "TextbookBM25-SysArch", "TextbookRRF-SysArch", "LanguageModelComponent-BpTTF"):
        node_means[nid] = round(statistics.mean(json.loads((RUN / (t["id"] + ".json")).read_text(encoding="utf-8"))["node_seconds"][nid] for t in dataset["tests"]), 3)
    summary = {"execution_ok": 20, "strict_pass": sum(r["strict_pass"] for r in records),
               "no_answer_refusal_pass": sum(r["no_answer_refusal_pass"] for r in records),
               "no_answer_strict_pass": sum(r["strict_pass"] for r in records if r["category"] == "无答案"),
               "retrieval": retrieval,
               "latency_seconds": {"mean": round(statistics.mean(times), 2), "median": round(statistics.median(times), 2),
                                   "p95_nearest_rank": sorted(times)[math.ceil(.95 * len(times)) - 1], "maximum": max(times)},
               "mean_node_seconds": node_means, "internal_marker_visible_count": sum(r["internal_marker_visible"] for r in records),
               "reviewer": "本助手逐题语义复核，非独立人工标注", "website_switched": False}
    (RUN / "review.json").write_text(json.dumps({"summary": summary, "questions": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "evaluation-details.md").write_text("\n".join(detail), encoding="utf-8")
    with (OUT / "evaluation-scores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["题号", "事实", "完整", "引用", "本轮严格通过", "前轮严格通过", "语义5参考命中", "融合5参考命中", "耗时秒", "审核说明"])
        for r in records:
            m = r["retrieval_metrics"]
            writer.writerow([r["id"], *r["scores"].values(), r["strict_pass"], r["baseline_strict_pass"],
                             m.get("same_run_dense5", {}).get("hit"), m.get("fused5", {}).get("hit"), r["elapsed_seconds"], r["review_note"]])
    report = ["# 关键词＋语义混合检索：第一轮实验报告", "", "## 已建立", "",
              "实验流程：**教材检索与备考问答 · 混合检索实验**。基于1616个真实正文分片，语义20候选与BM25关键词20候选，经等权RRF（常数60）去重取5片，再接原问答下游。没有新增大模型调用，仍为MiniMax-M3、温度0.2。", "",
              "本次只建立本地独立实验，**未替换正式流程或线上网页调用目标**。向量库未写入。关键词索引为固定快照，更新知识库后必须刷新。", "",
              "## 配置一致性", "",
              "初次检查发现当前正式流程已与上轮formula-fix版本不同：提示词、Parser和清理代码不一致，当前正式代码没有公式补充与新增占位清理。该差异来源本轮未查明。为排除干扰，仅在实验流程恢复上轮已验证的三个字段。提示、模型、温度、公式和清理代码哈希均与上轮基线对齐，正式流程保留开始时的状态。", "",
              "第一次诊断运行hybrid-20261008因此中止并单独标记，未混入分数。完整对照使用hybrid-verified-20261008，同一20题、独立会话、运行副本关闭聊天保存。", "",
              "## 检索结果", "", "| 检索方式 | 至少一个参考命中 / 18题 | 平均参考集合覆盖 | MRR |", "|---|---|---|---|"]
    labels = {"previous_dense5": "前轮语义前5", "same_run_dense5": "本轮语义前5（20候选池）", "bm25_5": "本轮BM25前5",
              "fused5": "本轮融合前5", "dense20": "本轮语义全部20候选", "bm25_20": "本轮BM25全部20候选"}
    for key, m in retrieval.items():
        report.append(f"| {labels[key]} | {m['hit_questions']}/18 | {100*m['mean_reference_coverage']:.1f}% | {m['mrr']:.4f} |")
    report += ["", "参考集合覆盖是每题已取回参考ID数/该题列出的参考ID数，再对18题平均；MRR是第一个参考的排名倒数平均。参考集合不是全书所有有效来源的全集，替代页可能有效；命中一个参考不等于覆盖多章节问题所有要点。", "",
               "**观察到的收益**：Q12原来语义第6名的完整动态模型说明，通过关键词第1名进入融合第2条；Q16语义第6名、关键词第4名的完整架构师任务段落进入融合第3条，支持此前遗漏的技术协调和文档化视图。", "",
               "**边界**：Q01第1章目标片段已在语义第11名，但BM25前20未取回，融合前5仍未包含。Q17两路前20都没有第9章MTTR段落，只融合排序无法恢复缺席的证据。这些适合下一阶段分问题检索、范围约束与重排序实验。", "",
               "## 答案与耗时", "", "| 指标 | 前轮formula-fix | 本轮混合检索 |", "|---|---|---|",
               f"| 执行成功 | 20/20 | 20/20 |",
               f"| 严格通过：事实/完整/引用均2分 | {baseline['summary']['strict_pass']}/20 | {summary['strict_pass']}/20 |",
               f"| 平均耗时 | {baseline['summary']['latency_seconds']['mean']}秒 | {summary['latency_seconds']['mean']}秒 |",
               f"| 中位耗时 | {baseline['summary']['latency_seconds']['median']}秒 | {summary['latency_seconds']['median']}秒 |",
               f"| 内部占位词可见 | 0题 | {summary['internal_marker_visible_count']}题 |", "",
               "两道虚构参数题均未编造端口或重试次数（拒绝行为2/2）；Q19附带说明的引用范围被缩写，所以严格评分的无答案题是1/2。拒绝行为与引用正确性分开记录。", "",
               f"评分由本助手逐题复核，未经独立人工标注。{summary['strict_pass']}/20不能称为全书准确率，更不能只凭单次差值保证稳定改善。模型生成有随机性，换上下文后原先通过的题也可能退步。", "",
               "**仍未解决**：Q09辅助段混用章节公式，Q12增加运行时限定，Q14辅助段的MTBF时间起点与含修复时间求和不一致，Q18仍加强原文力度并漏协议。混合检索改善证据获取，不能替代答案忠实度检查。", "",
               "新增BM25和RRF节点仍有解析/索引与DataFrame处理成本；两路可以并行，所以节点时间不能直接相加作为总响应时间。本轮平均总耗时下降也受生成篇幅、缓存及服务状态影响，不代表混合检索必然更快。", "",
               "| 节点 | 本轮平均记录耗时 |", "|---|---|"]
    for nid, seconds in node_means.items():
        report.append(f"| {nid} | {seconds}秒 |")
    report += ["", "## 建议如何继续学习", "",
               "先在实验流程查看Q12与Q16的两个候选列表和RRF排名，理解收益来自哪里；再研究Q01为何候选存在但排序未进前5，以及Q17为何需要跨章分问题。暂不根据20题定制答案规则或手工置顶分片。网页继续使用原流程，后续择定稳定版本再切换调用目标。", "",
               "## 逐题审核", "", "| 题号 | 前轮分 | 本轮事实/完整/引用 | 通过 | 说明 |", "|---|---|---|---|---|"]
    for r in records:
        report.append(f"| {r['id']} | {'/'.join(map(str,r['baseline_scores'].values()))} | {'/'.join(map(str,r['scores'].values()))} | {'是' if r['strict_pass'] else '否'} | {r['review_note']} |")
    report += ["", f"[学习指南与流程图]({OUT/'learning-guide.md'}) · [逐题实际答案]({OUT/'evaluation-details.md'}) · [评分CSV]({OUT/'evaluation-scores.csv'}) · [实验配置]({OUT/'setup.json'})", "",
               "方法来源：[BM25教材](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html)，[RRF原论文](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)。本机实现与实验结果见上述文件。"]
    (OUT / "experiment-report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
