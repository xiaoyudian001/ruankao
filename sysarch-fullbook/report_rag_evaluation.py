"""Summarize measured execution data and explicit semantic review, not keyword accuracy."""
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

ROOT=Path(r'F:\daily\output\sysarch-rag-evaluation')
RUN=ROOT/'baseline-20261008'
dataset=json.loads((ROOT/'dataset.json').read_text(encoding='utf-8'))
reviews={
 'Q01':([2,1,2],'检索未命中第1章参考分片，回答转向信息系统架构与软件架构，未完整回答一般系统架构的构成。其他引用本身有依据；问题未限定章节也增加歧义。',['检索偏题','问题范围较宽']),
 'Q02':([2,2,2],'第1章五项作用齐全，正确区分第7章另一组列表。',[]),
 'Q03':([2,2,2],'四层名称和职责齐全，页码与实际片段范围一致。',[]),
 'Q04':([2,2,2],'四部分及作用正确，简单项目可合并的条件保留。',[]),
 'Q05':([1,2,1],'主干定义正确，但把嵌入式操作系统微内核的优缺点混进一般插件架构；“不应直接调用、应通过内核或消息机制”并非第1章片段的明确要求。',['场景混淆','未支持的扩展']),
 'Q06':([2,2,2],'四种模型正确，补充与4+1视图的区别不影响核心答案。',[]),
 'Q07':([2,2,2],'三级模式、逻辑/物理区别和主要职责完整；答案较长，映象数量可由给出的结构图理解，未改变核心定义。',['较冗长']),
 'Q08':([2,2,2],'MTTF及不可修复系统含义正确，但用户可见答案出现formula-not-decoded内部占位词。该显示问题单列，不改变本题事实分。',['内部占位词外泄']),
 'Q09':([2,2,2],'第9章Restoration定义、时间组成和易恢复性结论完整。',[]),
 'Q10':([2,2,1],'可发现性及注册中心作用正确；补充的动态通讯录实现细节末尾再次附教材片段引用，未充分区分讲解推导与原文支持范围。',['辅助理解引用边界']),
 'Q11':([1,2,1],'核心区别完整，但比较表把框架模型的“研究核心”写成适应性结构，这是对原文目标描述的推导，未明确作为辅助理解。',['比较表添加推导']),
 'Q12':([1,2,1],'核心区别可用；把动态模型直接限定为运行时结构变化，并给过程模型添加预定义顺序的比较项，超出该片段明确表述，应独立标为推导。',['比较表添加推导','范围限定']),
 'Q13':([2,2,2],'服务对象和逻辑/物理描述内容区分正确。',[]),
 'Q14':([0,1,1],'未检索到含MTTF完整定义的参考分片，公式仅有占位。说明证据不足是合理的，但随后辅助补充同时给出MTBF=MTTF+MTTR和MTTF=MTBF=1/λ，与本题教材口径矛盾；且第9章MTTR全称被替换成Repair。',['公式解析缺失','检索证据不全','相互矛盾的公式','术语口径混用']),
 'Q15':([2,2,2],'架构师偏技术、项目经理偏资源/进度/成本，主对比及主要出处正确。末尾辅助段的片段1只有编号，页码完整性可改进。',['辅助段引用未写完整页码']),
 'Q16':([1,1,1],'检索到第7章可替代目的依据，但答案遗漏明确的协调技术活动、推动决策与文档化视图任务；比较表把“业务领域抽象建模”挂到不直接支持它的核心构架原文上。辅助比喻的“没有架构师就无法落地”也过强。',['必答任务遗漏','主题相关但非直接支持','辅助推导过强']),
 'Q17':([2,1,2],'第17章方向回答正确，也诚实说明未检索到第9章；两章综合证据不全，辅助讲解中有“MTBF在加，越往…”等不清晰措辞。',['跨段证据不足','措辞不清']),
 'Q18':([1,1,1],'网络公式正确，主要因素大致正确；把“减少MTTR也是有效途径”加强成“必须同时配合”，并漏答网络协议和理论公式实际计算局限。',['原文力度被加强','要点遗漏']),
 'Q19':([2,2,2],'正确说明当前片段不足，不编造端口或不存在的出处。引用编号指向检查过的片段，不作为产品参数证据。',[]),
 'Q20':([2,2,2],'正确说明当前片段不足，不编造重试次数或页码。',[])
}
assert len(reviews)==20
records=[]
details=['# 基线逐题答案与证据', '', '以下是2026-10-08真实执行结果；答案为MiniMax-M3输出，未改写。逐题评分由本助手对照原页、必答要点和实际context完成，未经过独立人工复核。','']
for t in dataset['tests']:
    r=json.loads((RUN/(t['id']+'.json')).read_text(encoding='utf-8'))
    assert r['id']==t['id'] and r['question']==t['question']
    scores,note,flags=reviews[t['id']]
    chunks=r['retrieved_chunks']; gold={s['chunk_id'] for s in t['gold_sources']}
    hit=bool(gold & {c.get('chunk_id') for c in chunks}) if gold else None
    cite_indices=[int(i) for i in re.findall(r'\[片段(\d+)',r['answer'])]
    invalid=[i for i in cite_indices if not 1<=i<=len(chunks)]
    formatting=bool(re.search(r'formula-not-decoded|\[公式占位\]|</?think>',r['answer'],re.I))
    records.append({'id':t['id'],'category':t['category'],'status':r['status'],
        'gold_hit_at_5':hit,'scores':dict(zip(['factual','completeness','citation'],scores)),
        'strict_pass':r['status']=='ok' and scores==[2,2,2],
        'elapsed_seconds':r['elapsed_seconds'],'invalid_citation_numbers':invalid,
        'internal_marker_visible':formatting, 'flags':flags,'review_note':note})
    details += [f"## {t['id']} · {t['category']}",'',t['question'],'',f"**评分（事实/完整/引用）**：{'/'.join(map(str,scores))}；{r['elapsed_seconds']}秒。",'',note,'','### 参考要点','']
    details += ['- '+p for p in t['required_points']]
    details += ['', '### 实际答案','',r['answer'],'','### 本次检索','', '| 排名 | 教材页 | PDF页 | 分片ID | 原始分值 |','|---|---|---|---|---|']
    for i,c in enumerate(chunks):
        details.append(f"| {i+1} | {c.get('book_pages') or '映射不完整/无'} | {c.get('pdf_pages','')} | `{c.get('chunk_id','')[:12]}` | {c.get('_score','')} |")
    details += ['',f"[同次执行完整context和检索片段]({RUN.name}/{t['id']}.json)",'']
    for p in sorted({p for s in t['gold_sources'] for p in s['gold_pdf_pages']}):
        details.append(f'[核对PDF第{p}页](evidence/pdf-{p:03}.png)')
    details.append('')

times=[r['elapsed_seconds'] for r in records if r['status']=='ok']
answerable=[r for r in records if r['gold_hit_at_5'] is not None]
strict=sum(r['strict_pass'] for r in records)
summary={'execution_ok':sum(r['status']=='ok' for r in records),'questions':len(records),
 'strict_pass':strict,'gold_hit_at_5':{'hit':sum(r['gold_hit_at_5'] for r in answerable),'answerable':len(answerable)},
 'no_answer_pass':sum(r['strict_pass'] for r in records if r['category']=='无答案'),
 'latency_seconds':{'mean':round(statistics.mean(times),2),'median':round(statistics.median(times),2),
 'p95_nearest_rank':sorted(times)[math.ceil(.95*len(times))-1], 'maximum':max(times)},
 'internal_marker_visible_count':sum(r['internal_marker_visible'] for r in records),
 'invalid_citation_number_count':sum(len(r['invalid_citation_numbers']) for r in records),
 'reviewer':'本助手逐题语义审核；非独立人工标注，建议用户复核争议项',
 'metrics_note':'本次20题单次运行、非随机样本；严格通过率不能等同全书准确率；未匹配参考chunk不等同检索毫无相关依据'}
(RUN/'review.json').write_text(json.dumps({'summary':summary,'questions':records},ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'baseline-scores.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['编号','类型','执行状态','事实0-2','完整0-2','引用0-2','严格通过','参考分片命中@5','耗时秒','问题标签','审核说明'])
    for r in records:
        w.writerow([r['id'],r['category'],r['status'],*r['scores'].values(),r['strict_pass'],r['gold_hit_at_5'],r['elapsed_seconds'],'；'.join(r['flags']),r['review_note']])
(ROOT/'baseline-details.md').write_text('\n'.join(details),encoding='utf-8')
cfg=json.loads((RUN/'configuration.json').read_text(encoding='utf-8'))
report=['# 教材RAG基线报告 · 2026-10-08','',
 '## 本次测试','',
 '使用当前「教材检索与备考问答」流程：MiniMax-M3、温度0.2、SysArchTutorRAGv3、Top K=5、仅检索正文。20题独立会话、逐题顺序调用，保留同次执行的真实检索片段、context和答案。', '',
 '没有修改正式流程；测试运行副本仅关闭聊天消息保存。正常认证的构建接口可用，旧/run/session路径已不适用；未关闭认证，也未改变网站连接程序。', '',
 '## 实测结果','',
 '| 指标 | 结果 |','|---|---|',
 f"| 执行成功 | {summary['execution_ok']}/20 |",f'| 严格通过（事实/完整/引用均2分） | {strict}/20 |',
 f"| 前5条至少命中一个参考分片（18题有答案） | {summary['gold_hit_at_5']['hit']}/18 |",
 f"| 无答案题正确拒绝编造 | {summary['no_answer_pass']}/2 |",
 f"| 平均 / 中位耗时 | {summary['latency_seconds']['mean']} / {summary['latency_seconds']['median']}秒 |",
 f"| P95 / 最长耗时 | {summary['latency_seconds']['p95_nearest_rank']} / {summary['latency_seconds']['maximum']}秒 |",
 f"| 用户答案中可见内部占位词 | {summary['internal_marker_visible_count']}题 |",
 f"| 不存在的片段引用编号 | {summary['invalid_citation_number_count']}个 |",'',
 '评分由本助手逐题语义审核，未经过独立人工复核；严格通过不是“回答完全没用”与“完全正确”的二分准确率。执行成功不代表答案正确。参考分片集合非穷尽：其他页也可能提供有效答案。P95采用最近秩法；这是顺序本机测试，包含检索、网络生成和清理，不能代表多人并发或每次运行。','',
 '## 主要发现及下一步','',
 '1. **先修公式来源（Q14）**：原PDF第323页公式存在，但分片中未完整识别。应补入核对后的公式或结构化公式证据，保留适用条件及第9/17章统计口径。模型缺证据时不能用相互矛盾的通用公式补齐。',
 '2. **改善检索范围（Q01、Q17）**：定义题偏向组织级信息系统；跨章题仅取回第17章。下一轮可比较关键词+向量混合检索、重排序与分问题检索，记录是否获得本题各方面的证据；题目有歧义时也需澄清范围。',
 '3. **收紧教材与讲解边界（Q05、Q10～12、Q16、Q18）**：不同场景混合、比较表自行补项、把有效途径变成必须条件仍会发生。增加证据核对与条件保留，并把未直接支持的推导标明为辅助理解。',
 '4. **补显示清理（Q08）**：已隐藏think区域，但formula-not-decoded仍能出现在答案；应只说明公式未完整识别。',
 '5. **保持固定对照**：先改一个因素，再运行同样20题。当前不同时改模型、温度、切片、检索方式，便于判断改善来自哪一步。','',
 '这些改进尚未实施，本次交付是测试集和当前基线。','',
 '## 逐题摘要','',
 '| 题号 | 类型 | 事实/完整/引用 | 通过 | 参考命中 | 秒 | 检查意见 |','|---|---|---|---|---|---|---|']
for r in records:
    report.append(f"| {r['id']} | {r['category']} | {'/'.join(map(str,r['scores'].values()))} | {'是' if r['strict_pass'] else '否'} | {'不适用' if r['gold_hit_at_5'] is None else '是' if r['gold_hit_at_5'] else '否'} | {r['elapsed_seconds']} | {r['review_note']} |")
report += ['', '## 文件与复用','',
 '[测试题和参考答案](test-set.md) · [测试表CSV](test-set.csv) · [逐题实际答案](baseline-details.md) · [评分表CSV](baseline-scores.csv) · [使用方法](README.md)', '',
 '原页核对使用此前保存的分段PDF；整本原PDF记录路径当前不可用，未重新核验整本文件哈希。12页可视证据在evidence目录；机器数据在dataset.json。', '',
 f"流程指纹：`{cfg['flow_sha256']}`。本次结束复核正式流程指纹一致。"]
(ROOT/'baseline-report.md').write_text('\n'.join(report),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
