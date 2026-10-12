"""Source-bound restoration of visually reviewed PDF evidence, independent of question text."""
_FORMULA_SOURCE_SHA = 'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'
_FORMULA_CHUNK_IDS = {
    '24dab5987badacf1a610882a627f5e72f8ae1b1194e5373ac3977febf854403f',
    '64fd09659c004992c101e9d85668764c45a7e2417a5fa5b9355089f0b3b0e791',
}
_FORMULA_EVIDENCE_MARKER = '【原页核对补充：教材第308页（PDF第323页）】'
_FORMULA_EVIDENCE = r'''【原页核对补充：教材第308页（PDF第323页）】
以下是第9章该页相关原文及公式的核对转录，补齐OCR分片中的公式缺失和段落截断；不是模型的辅助讲解。

5. 平均失效前时间
可靠度为R(t)的系统平均失效前时间（Mean Time To Failure，MTTF）定义为从t=0时到故障发生时系统的持续运行时间的期望值：
$$MTTF = \int_{0}^{\infty} R(t)\,dt$$
对于不可修复系统，系统的平均寿命指系统发生失效前的平均工作（或存储）时间或工作次数，也称为系统在失效前的平均时间。

6. 平均恢复前时间
平均恢复前时间（Mean Time To Restoration，MTTR）是随机变量恢复时间的期望值，就是从出现故障到修复成功中间的这段时间，它包括确认失效发生所必需的时间，记录所有任务的时间，还有将设备重新投入使用的时间。MTTR越短表示易恢复性越好。

7. 平均故障间隔时间
MTBF（Mean Time Between Failures，平均故障间隔时间）定义为：失效或维护中所需的平均时间，包括故障时间以及检测和维护设备的时间。
对于可靠度服从指数分布的系统，从任一时刻t₀到达故障的期望时间都是相等的，因此有：
$$MTBF = MTTF + MTTR$$'''


def enrich_formula_evidence(row):
    result = dict(row)
    pages = {p.strip() for p in str(row.get('pdf_pages', '')).split(',')}
    if (row.get('source_sha256') != _FORMULA_SOURCE_SHA
            or row.get('chunk_id') not in _FORMULA_CHUNK_IDS or '323' not in pages):
        return result
    # Check both explicit pages and the citation range before attaching evidence.
    try:
        first, last = int(row.get('pdf_page_start', '')), int(row.get('pdf_page_end', ''))
    except (TypeError, ValueError):
        return result
    if not first <= 323 <= last:
        return result
    content = str(row.get('content', ''))
    if _FORMULA_EVIDENCE_MARKER not in content:
        result['content'] = content + '\n\n' + _FORMULA_EVIDENCE
    return result
