"""Compare the unchanged evaluation questions using explicit semantic reviews."""
import csv
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(r"F:\daily\output\sysarch-rag-evaluation")
RUN = ROOT / "formula-fix-20261008"
AUDIT = Path(r"F:\daily\output\sysarch-formula-fix")

# These are reviews of the saved answers and same-run evidence, not keyword scores.
REVIEWS = {
    "Q01": ([2, 1, 2], "仍未命中第1章一般系统架构定义；组织级与软件级架构的回答有出处，但一般构成未完整回答。", ["检索范围"]),
    "Q02": ([2, 2, 2], "五项作用完整，引用对应实际片段。", []),
    "Q03": ([2, 2, 2], "分层四部分、职责与引用完整。", []),
    "Q04": ([2, 2, 2], "事件驱动四部分及作用完整，保留简单项目可合并的条件。", []),
    "Q05": ([1, 2, 2], "主干定义及引用正确，辅助段仍把插件不直接互调、经内核协调和替换不影响其他插件写成确定机制；给定教材未明确要求或保证。", ["辅助扩展缺依据"]),
    "Q06": ([2, 2, 2], "四种模型名称与说明正确。", []),
    "Q07": ([2, 2, 2], "三级模式与主要职责完整；映象关系的讲解与给出的结构相符。", []),
    "Q08": ([2, 2, 1], "MTTF定义和积分公式正确，内部占位词消失；合并引用片段1/2时将片段2的教材307～308/PDF322～323范围缩为308/323，不符合当前完整复制source_hint规则。", ["引用范围缩写"]),
    "Q09": ([2, 2, 2], "第9章Restoration定义、三项时间组成和易恢复性结论正确，引用范围完整。", []),
    "Q10": ([2, 2, 1], "可发现性与注册中心主干正确，但主段把集中存储、通知平台等实现讲解挂到教材引用上，原片段未完整支持这些细节。", ["讲解引用边界"]),
    "Q11": ([2, 2, 2], "结构模型与框架模型区别正确；明确说明框架模型研究核心未单独列出，没有再把推导当成教材分类。", []),
    "Q12": ([2, 2, 1], "去掉了运行时限定和预定义顺序的断言，核心区别正确；比较表仍把“做什么/怎么做”的教学概括混入教材依据部分。", ["比较表推导边界"]),
    "Q13": ([2, 2, 1], "外模式与内模式的对象及内容正确；片段3的教材223～224/PDF238～239多次被缩成223/238，未完整复制来源范围。", ["引用范围缩写"]),
    "Q14": ([2, 2, 2], "正确给出MTTF积分、MTTR的Restoration口径，并保留可靠度服从指数分布时MTBF=MTTF+MTTR的条件；不再出现MTTF=MTBF=1/λ的矛盾补充，引用片段2单页正确。", []),
    "Q15": ([2, 2, 2], "架构师与项目经理的技术/资源进度成本侧重正确，主要出处及辅助段页码完整。", []),
    "Q16": ([2, 1, 1], "核心转化路径有教材支持，取消了过强比喻；仍遗漏参考任务中的协调技术活动和不同视图，且将只有标题的管理复杂性条目扩为具体分解与抽象手段。", ["任务要点不全", "主题相关但非直接支持"]),
    "Q17": ([1, 1, 1], "仍只取回第17章，诚实说明缺第9章但又说标准术语含义一致；没有证据支持跨章口径等同，辅助段将两个方向直接等同完整MTTR组成也过强。", ["跨章检索不全", "术语口径混用"]),
    "Q18": ([1, 1, 1], "可用性公式正确；依然将减少MTTR也是有效途径加强成必须同时考虑，主要依据部分漏网络协议和理论公式实际计算局限；辅助段提协议未补足教材依据。", ["原文力度加强", "要点遗漏"]),
    "Q19": ([2, 2, 2], "正确拒绝编造默认端口及不存在的教材出处。", []),
    "Q20": ([2, 2, 2], "正确拒绝编造框架重试次数；即使召回含公式页也未强行作答。", []),
}


def main():
    dataset = json.loads((ROOT / "dataset.json").read_text(encoding="utf-8"))
    frozen = json.loads((RUN / "dataset-used.json").read_text(encoding="utf-8"))
    assert dataset == frozen, "Evaluation dataset changed"
    baseline = json.loads((ROOT / "baseline-20261008" / "review.json").read_text(encoding="utf-8"))
    before = {q["id"]: q for q in baseline["questions"]}
    records = []
    details = ["# 公式修复复测：逐题实际答案", "",
               "20道题与基线相同。评分由本助手对照必答要点、保存的同次context和已核对原页完成，未经独立人工复核。答案保持原样。", ""]
    for test in dataset["tests"]:
        qid = test["id"]
        saved = json.loads((RUN / f"{qid}.json").read_text(encoding="utf-8"))
        assert saved["question"] == test["question"]
        assert saved["status"] == "ok"
        scores, note, flags = REVIEWS[qid]
        chunks = saved["retrieved_chunks"]
        gold = {s["chunk_id"] for s in test["gold_sources"]}
        hit = bool(gold & {c.get("chunk_id") for c in chunks}) if gold else None
        indices = [int(n) for n in re.findall(r"\[片段(\d+)", saved["answer"])]
        invalid = [n for n in indices if not 1 <= n <= len(chunks)]
        marker = bool(re.search(r"formula-not-decoded|\[公式占位\]|</?think>", saved["answer"], re.I))
        old = before[qid]
        record = {
            "id": qid, "category": test["category"], "status": saved["status"],
            "scores": dict(zip(["factual", "completeness", "citation"], scores)),
            "strict_pass": scores == [2, 2, 2], "gold_hit_at_5": hit,
            "elapsed_seconds": saved["elapsed_seconds"],
            "internal_marker_visible": marker, "invalid_citation_numbers": invalid,
            "baseline_scores": old["scores"], "baseline_strict_pass": old["strict_pass"],
            "flags": flags, "review_note": note,
        }
        records.append(record)
        details += [f"## {qid} · {test['category']}", "", test["question"], "",
                    f"事实/完整/引用：{'/'.join(map(str, scores))}；{saved['elapsed_seconds']}秒。", "", note,
                    "", "### 参考要点", ""]
        details += ["- " + p for p in test["required_points"]]
        details += ["", "### 实际答案", "", saved["answer"], "", "### 实际检索", "",
                    "| 排名 | 教材页 | PDF页 | 分片ID |", "|---|---|---|---|"]
        for rank, chunk in enumerate(chunks, 1):
            details.append(f"| {rank} | {chunk.get('book_pages', '')} | {chunk.get('pdf_pages', '')} | `{chunk.get('chunk_id', '')}` |")
        details += ["", f"[同次完整context与答案]({RUN / (qid + '.json')})", ""]

    q14 = json.loads((RUN / "Q14.json").read_text(encoding="utf-8"))
    assert "原页核对补充" in q14["context"]
    assert "平均恢复前时间" in q14["answer"] and "指数" in q14["answer"]
    assert "Repair" not in q14["answer"]
    assert "MTTF + MTTR" in q14["answer"] or "MTTF+MTTR" in q14["answer"]
    assert not re.search(r"1\s*/\s*[λ\\]", q14["answer"])
    assert all(not r["internal_marker_visible"] for r in records)
    run_summary = json.loads((RUN / "run-summary.json").read_text(encoding="utf-8"))
    assert run_summary["flow_unchanged"]
    assert len(records) == 20 and len(REVIEWS) == 20
    times = [r["elapsed_seconds"] for r in records]
    answerable = [r for r in records if r["gold_hit_at_5"] is not None]
    summary = {
        "execution_ok": 20, "questions": 20,
        "strict_pass": sum(r["strict_pass"] for r in records),
        "gold_hit_at_5": {"hit": sum(r["gold_hit_at_5"] for r in answerable), "answerable": len(answerable)},
        "no_answer_pass": sum(r["strict_pass"] for r in records if r["category"] == "无答案"),
        "latency_seconds": {"mean": round(statistics.mean(times), 2), "median": round(statistics.median(times), 2),
                            "p95_nearest_rank": sorted(times)[math.ceil(.95 * len(times)) - 1], "maximum": max(times)},
        "internal_marker_visible_count": sum(r["internal_marker_visible"] for r in records),
        "invalid_citation_number_count": sum(len(r["invalid_citation_numbers"]) for r in records),
        "reviewer": "本助手逐题语义审核；非独立人工复核",
        "metrics_note": "固定20题单次运行；不代表全书准确率。前5条至少一个参考分片命中，不等于召回齐所有必答证据。",
    }
    (RUN / "review.json").write_text(json.dumps({"summary": summary, "questions": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "formula-fix-details.md").write_text("\n".join(details), encoding="utf-8")
    with (ROOT / "formula-fix-scores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["编号", "类型", "事实", "完整", "引用", "严格通过", "基线严格通过", "参考命中@5", "耗时秒", "审核说明"])
        for r in records:
            writer.writerow([r["id"], r["category"], *r["scores"].values(), r["strict_pass"], r["baseline_strict_pass"], r["gold_hit_at_5"], r["elapsed_seconds"], r["review_note"]])

    b = baseline["summary"]
    report = ["# 教材公式证据与回答边界修复：对照报告", "", "## 已生效的改动", "",
              "正式流程「教材检索与备考问答」已保存三个字段的变化：Parser代码、提示模板、最终答案清理代码。模型仍为MiniMax-M3、温度0.2、知识库SysArchTutorRAGv3、Top K=5、仅正文；连线与其他字段未改变。", "",
              "1. **恢复核对后的公式证据**：教材第308页（PDF第323页）的MTTF定义与积分公式、MTTR的Restoration定义、指数分布条件下MTBF=MTTF+MTTR，经原页核对后，在整理检索文本时补充到对应两个分片。来源哈希、分片ID、页码须同时匹配；补充与问题文字无关，未新增向量或改变原始OCR。",
              "2. **收紧提示规则**：禁止在缺公式时猜补；要求保留适用条件、区分章节统计口径、把推导与教材依据分开，不加强原文结论。",
              "3. **清理显示**：保留已有think清理，将内部公式占位转换为“公式未完整识别”，保留有效数学公式与引用。", "",
              "## 同20题复测", "", "| 指标 | 基线 | 本次 |", "|---|---|---|"]
    for label, old, new in [
        ("执行成功", f"{b['execution_ok']}/20", "20/20"),
        ("严格通过：事实/完整/引用均2分", f"{b['strict_pass']}/20", f"{summary['strict_pass']}/20"),
        ("前5条至少命中一个参考分片", f"{b['gold_hit_at_5']['hit']}/18", f"{summary['gold_hit_at_5']['hit']}/18"),
        ("无答案题不编造", f"{b['no_answer_pass']}/2", f"{summary['no_answer_pass']}/2"),
        ("平均耗时", f"{b['latency_seconds']['mean']}秒", f"{summary['latency_seconds']['mean']}秒"),
        ("中位耗时", f"{b['latency_seconds']['median']}秒", f"{summary['latency_seconds']['median']}秒"),
        ("P95（最近秩）", f"{b['latency_seconds']['p95_nearest_rank']}秒", f"{summary['latency_seconds']['p95_nearest_rank']}秒"),
        ("内部占位词可见", f"{b['internal_marker_visible_count']}题", f"{summary['internal_marker_visible_count']}题"),
    ]:
        report.append(f"| {label} | {old} | {new} |")
    report += ["", "评分是本助手的逐题语义审核，未经独立人工复核。使用同一问题和原评分维度，但模型生成仍有随机性；本次改了三个相关字段，不能把所有变化归因于某一条提示。单次耗时不代表稳定性能，严格通过率不等于全书准确率。", "",
               "## 改善与未解决的问题", "",
               "- **Q14公式比较题已修复**：事实/完整/引用从0/1/1变为2/2/2。公式及其指数分布条件正确，第9章使用Restoration口径，矛盾的1/λ补充消失。单次耗时由77.612秒降为18.182秒。",
               "- **Q11比较题改善**：不再把框架模型的研究核心自行补成教材分类。Q12、Q16也有局部改善，但未全部通过。",
               "- **总体严格通过仍是11/20**：Q11、Q14新增通过；Q08、Q13此次生成答案缩写多页来源范围，按当前完整复制source_hint规则失去严格通过。引用指向真实片段，但未完整保留片段的页范围。",
               "- **检索缺证据仍在**：Q01没有取到第1章一般架构定义，Q17没有取到第9章，不能用补充第323页的证据规则解决未召回该页的情况。",
               "- **只靠提示不能保证边界**：Q05仍增加插件调用机制断言，Q17仍泛化跨章术语一致，Q18仍把有效途径加强为必须条件。保留失败评分，未把局部修复算成全部解决。", "",
               "本轮只恢复已核对的教材第308页相关公式，其他页的公式缺失仍需原页复核。没有重解析全书、重建向量库或添加混合检索/重排序。", "",
               "## 下一阶段", "",
               "优先使引用页范围由实际检索元数据确定并校验，减少模型改写页码；再分别比较混合检索、重排序或跨章分问题检索，重点复核Q01/Q17。教材与讲解的边界需逐题复核，不能只看执行成功率。", "",
               "## 验证与回退", "",
               "- 修复前回归检查有3项失败；修复后5项通过，覆盖原页公式、来源守卫、纯函数与幂等、think及占位清理、未核对公式不猜补。",
               "- PATCH后读回确认只有3个目标字段变化，所有连线及其他配置相同；20题运行前后正式流程指纹一致。",
               f"- [字段备份及回退值]({AUDIT / 'rollback-fields.json'})保存3个字段的before/after；回退前须读取正式流程并确认对应字段仍等于after，避免覆盖后续编辑。",
               f"- [核对证据清单]({AUDIT / 'verified-evidence.json'}) · [激活记录]({AUDIT / 'activation.json'}) · [原页图像]({ROOT / 'evidence' / 'pdf-323.png'})", "",
               "## 逐题对照", "", "| 题号 | 基线分 | 本次分 | 本次通过 | 审核说明 |", "|---|---|---|---|---|"]
    for r in records:
        report.append(f"| {r['id']} | {'/'.join(map(str, r['baseline_scores'].values()))} | {'/'.join(map(str, r['scores'].values()))} | {'是' if r['strict_pass'] else '否'} | {r['review_note']} |")
    report += ["", f"[逐题原始答案与出处]({ROOT / 'formula-fix-details.md'}) · [评分CSV]({ROOT / 'formula-fix-scores.csv'}) · [原基线报告]({ROOT / 'baseline-report.md'})", ""]
    (AUDIT / "verification-report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
