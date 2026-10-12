"""Build a fixed, original-page-checked evaluation set; never infer gold from model answers."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r'F:\daily\output\sysarch-rag-evaluation')
CORPUS = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark\final_chunks.json')
rows = json.loads(CORPUS.read_text(encoding='utf-8'))
page_map = json.loads(Path(r'F:\daily\output\sysarch-page-citations\page-map.json').read_text(encoding='utf-8'))['pages']

def source(prefix, pages):
    matches = [r for r in rows if r['id'].startswith(prefix)]
    assert len(matches) == 1, prefix
    r = matches[0]
    return {'chunk_id': r['metadata']['chunk_id'], 'chroma_id': r['id'],
            'gold_pdf_pages': pages, 'gold_book_pages': [page_map[str(p)]['book_page'] for p in pages],
            'chapter': r['metadata'].get('chapter'), 'cached_ocr_excerpt': r['content'],
            'verified_page_images': [f'evidence/pdf-{p:03}.png' for p in pages],
            'note': '参考答案与页面图像核对；OCR片段保留原样，公式和误字可能未被正确入库。'}

tests = []
def add(category, question, points, refs, risk):
    tests.append({'id': f'Q{len(tests)+1:02}', 'category': category, 'question': question,
                  'reference_answer': '；'.join(points) + '。', 'required_points': points,
                  'gold_sources': [source(p, pages) for p, pages in refs],
                  'failure_checks': risk, 'answerable': category != '无答案',
                  'review': {'factual_score_0_2': None, 'completeness_score_0_2': None,
                             'citation_score_0_2': None, 'notes': ''}})

add('定义列举', '依据教材，系统架构是什么？由哪些内容构成？请给出教材和PDF页码。',
    ['系统整体的高层次结构表示，是系统的骨架和根基', '包括组件、连接件、约束规范及指导设计与演化的原理'],
    [('060c68fd044a',[19])], ['不能只给组件清单而遗漏高层次结构含义'])
add('定义列举', '教材列举了架构设计的哪五项主要作用？请完整列出并给出出处。',
    ['解决相对复杂的需求分析问题', '解决非功能属性占重要位置的设计问题', '解决生命周期长、扩展性需求高的整体结构问题', '解决基于组件的集成问题', '解决业务流程再造难的问题'],
    [('060c68fd044a',[19])], ['检查五项是否齐全，不能用常识替换教材条目'])
add('定义列举', '教材中的典型四层分层架构包括哪四层？分别负责什么？',
    ['表现层：用户界面，负责视觉和用户互动', '业务层：实现业务逻辑', '持久层：提供数据，SQL语句放在这一层', '数据库层：保存数据'],
    [('aef745c11d70',[24,25])], ['不要把持久层和数据库层合并成一层'])
add('定义列举', '事件驱动架构由哪四个部分组成？分别起什么作用？请附出处。',
    ['事件队列：接收事件的入口', '分发器：将事件分发到不同业务逻辑单元', '事件通道：分发器与处理器之间的联系渠道', '事件处理器：实现业务逻辑，完成后发出事件触发下一步'],
    [('488ea4f01273',[25,26])], ['不要用事件生产者/消费者等其他模型替换教材四部分'])
add('定义列举', '什么是微核架构？内核和插件分别负责什么？插件之间能否通信？',
    ['又称插件架构，软件内核相对较小', '内核通常只包含系统运行的最小功能', '主要功能和业务逻辑通过插件实现', '插件互相独立，应把插件间通信减少到最低，避免相互依赖'],
    [('488ea4f01273',[26])], ['“减少到最低”不能被改成“完全禁止通信”'])
add('定义列举', '教材介绍的软件架构建模方法分为哪四种模型？',
    ['结构模型', '框架模型', '动态模型', '过程模型'],
    [('841c81c1d92b',[28])], ['不要与五种常见架构或4+1视图混淆'])
add('定义列举', '数据库的三级模式是什么？分别描述什么？',
    ['外模式：用户所需部分数据的逻辑结构和特征，是用户与系统的接口', '概念模式：全部数据的逻辑结构和特征，包括联系、操作、完整性与安全约束，不涉及物理存储和硬件细节', '内模式：物理结构与存储方式，包括记录、索引、文件组织等'],
    [('70c708251f15',[238,239]),('a862bbab0710',[239])], ['不能把概念模式说成物理存储结构'])
add('定义列举', '教材第9章如何定义MTTF？对于不可修复系统，它表示什么？',
    ['平均失效前时间，Mean Time To Failure', '从t=0到故障发生的持续运行时间的期望值', '对不可修复系统表示失效前平均工作或存储时间、或工作次数'],
    [('101f2aa5a56c',[323])], ['不要把MTTF答成修复时间或不加条件等同MTBF'])
add('定义列举', '依据第9章，MTTR是什么？恢复时间包括哪些部分，数值越短说明什么？',
    ['平均恢复前时间，Mean Time To Restoration，是恢复时间的期望值', '从出现故障到恢复成功的这段时间', '包括确认失效、记录所有任务、将设备重新投入使用所需时间', 'MTTR越短，易恢复性越好'],
    [('101f2aa5a56c',[323])], ['区分第9章Restoration与第17章Repair的教材用词'])
add('定义列举', '云原生架构中，微服务的可发现性是什么？服务注册中心起什么作用？',
    ['服务A发布或扩缩容时，依赖它的B无需重新发布即可自动感知A的变化', '引入第三方服务注册中心满足可发现性', '大规模集群尤其重视注册中心的推送和扩展能力'],
    [('6c24ae3f0c86',[510])], ['不要只回答“通过REST调用”，那是可交互性'])
add('比较', '结构模型与框架模型有什么区别？依据教材比较描述重点。',
    ['结构模型描述构件、连接件等结构，语义、配置、约束、假设和风格性质，核心是架构描述语言', '框架模型类似结构模型，但更少关注结构细节，更关注整体结构，主要针对特殊问题'],
    [('841c81c1d92b',[28])], ['不得把框架模型描述为更详细的构件模型'])
add('比较', '动态模型与过程模型有什么区别？各自关注什么？',
    ['动态模型补充结构或框架模型，研究大颗粒行为、重配置与演化，以及通信或计算创建和删除', '过程模型研究系统构造步骤和过程，结构是遵循过程脚本的结果'],
    [('841c81c1d92b',[28])], ['不要混同运行时行为与构造过程'])
add('比较', '数据库外模式与内模式有什么不同？从面向对象和描述内容两个方面比较。',
    ['外模式面向用户或应用，只描述所需部分数据的逻辑结构和特征', '内模式面向数据存储，描述物理结构和存储方式，如记录、索引和文件组织'],
    [('a862bbab0710',[239])], ['“面向对象”指服务对象，不是要求介绍面向对象数据库'])
add('比较', '依据第9章，比较MTTF与MTTR，并说明在教材给出的指数分布条件下，它们与MTBF有什么关系。',
    ['MTTF衡量失效前持续运行时间的期望值', 'MTTR衡量故障出现至恢复成功的恢复时间期望值', '在教材给出的可靠度服从指数分布条件下，MTBF=MTTF+MTTR'],
    [('101f2aa5a56c',[323]),('22dcb120b49f',[323])], ['公式须与PDF核对：入库文本可能只剩[公式占位]', '不能省略问题要求的指数分布条件'])
add('比较', '依据教材，系统架构设计师与项目经理的工作侧重点有什么不同？',
    ['架构设计师负责架构设计、关键技术细节及技术决策，是项目技术领导', '项目经理侧重项目资源、进度和成本管理'],
    [('b2b871bc5cd2',[30])], ['不要把两者职责完全互斥化或杜撰人事汇报关系'])
add('跨段综合', '结合架构设计的目的和架构设计师的任务，说明架构师如何把需求转成可实现的系统。请分别引用两处教材依据。',
    ['架构设计通过相关抽象指导系统各方面的设计与实现', '架构师领导协调分析、设计和实施的技术活动', '推动主要技术决策并形成架构表述', '确定和文档化架构，包括需求、设计、实施及部署视图'],
    [('060c68fd044a',[19]),('b2b871bc5cd2',[30])], ['综合题须覆盖目的和人员任务两个证据方面'])
add('跨段综合', '结合第9章MTTR定义与第17章网络高可用设计，说明降低MTTR为何有效，以及可从哪两个方向着手。',
    ['第9章：MTTR涵盖从故障出现到恢复成功的时间，越短易恢复性越好', '第17章：网络故障恢复时间影响可用性，减少MTTR是有效途径', '尽快发现网络故障', '迅速将网络从故障状态恢复出来'],
    [('101f2aa5a56c',[323]),('d80439049f32',[628]),('02633f319460',[628])], ['必须给出两个改进方向及两章依据'])
add('跨段综合', '教材用MTBF和MTTR给出了什么网络可用性公式？为什么不能只靠不断提高MTBF？哪些系统因素也影响网络高可用性？',
    ['第17章网络口径下，A=MTBF/(MTBF+MTTR)', '设备硬件与软件质量提升有限，不能一味提高MTBF，降低MTTR同样有效', '网络是系统整体，部件可用性和连接模型共同影响高可用性', '网络协议等因素也需考虑，理论公式难以精确计算实际网络，通常采用工程经验公式'],
    [('d80439049f32',[628]),('02633f319460',[628,629])], ['勿混入第9章MTBF=MTTF+MTTR关系而改变本题公式口径', '不能把单个部件高可用性直接等同整个网络'])
add('无答案', '只依据这本教材：NebulaGhost2099量子路由器的默认管理端口是多少？请给出教材出处。',
    ['明确表示当前教材检索片段未提供该虚构产品的端口信息，无法依据教材确定', '不编造端口、页码或依据；可请用户提供产品资料'],
    [], ['不得把常见端口80/443/22当作该产品的事实'])
add('无答案', '只依据这本教材：AuroraMeshX2099框架默认事件重试次数是多少？没有明确记载就说明无法确定。',
    ['明确表示当前教材检索片段未提供该虚构框架的默认重试次数', '不编造具体次数或教材引用；可请用户提供框架文档'],
    [], ['事件驱动相关片段不构成该产品参数的证据'])

assert Counter(t['category'] for t in tests) == {'定义列举':10,'比较':5,'跨段综合':3,'无答案':2}
for name in ('NebulaGhost2099','AuroraMeshX2099'):
    assert not any(name.lower() in r['content'].lower() for r in rows)
ROOT.mkdir(parents=True, exist_ok=True)
dataset = {'version':'sysarch-rag-eval-v1', 'created':'2026-10-08', 'language':'zh-CN',
           'source_title':'系统架构设计师教程（第2版）',
           'source_sha256':rows[0]['metadata']['source_sha256'],
           'corpus_sha256':hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
           'verification':'已视觉核对12页；使用原文保存的分段PDF。原整本PDF记录路径当前不可用，未重新核验整本文件哈希。',
           'question_selection':'由本助手逐题选取并依据原页整理参考答案，未由被测MiniMax模型生成；非随机样本，不代表全书准确率。',
           'tests':tests}
(ROOT/'dataset.json').write_text(json.dumps(dataset,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'test-set.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['编号','类型','问题','参考答案','原文核对页(PDF)','教材页','风险检查','事实分0-2','完整分0-2','引用分0-2','备注'])
    for t in tests:
        pp=sorted({p for s in t['gold_sources'] for p in s['gold_pdf_pages']})
        bp=sorted({p for s in t['gold_sources'] for p in s['gold_book_pages'] if p is not None})
        w.writerow([t['id'],t['category'],t['question'],t['reference_answer'],','.join(map(str,pp)),','.join(map(str,bp)),'；'.join(t['failure_checks']),'','','',''])
lines=['# 教材 RAG 固定测试集（20题）','', '10题定义列举、5题比较、3题跨段综合、2题无答案。参考答案已核对原页；下一次改配置时使用相同问题。','']
for t in tests:
    pp=sorted({p for s in t['gold_sources'] for p in s['gold_pdf_pages']})
    bp=sorted({p for s in t['gold_sources'] for p in s['gold_book_pages'] if p is not None})
    lines += [f"## {t['id']} · {t['category']}", '', t['question'], '', '**参考要点**','']
    lines += ['- '+p for p in t['required_points']]
    lines += ['',f"**原文**：教材页 {','.join(map(str,bp)) or '不适用'}；PDF页 {','.join(map(str,pp)) or '不适用'}。",'']
    lines += [f'- [核对PDF第{p}页](evidence/pdf-{p:03}.png)' for p in pp]
    lines += ['', '**检查**：'+'；'.join(t['failure_checks']), '']
(ROOT/'test-set.md').write_text('\n'.join(lines),encoding='utf-8')
print('Created 20 questions:', dict(Counter(t['category'] for t in tests)))
