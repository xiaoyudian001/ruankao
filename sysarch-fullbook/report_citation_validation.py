"""Generate a user-facing report only after final saved-flow checks succeed."""
from pathlib import Path
import json

ROOT=Path(r'F:\daily\output\sysarch-citation-validation')


def main():
    v=json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
    assert v['knowledge_rows_unchanged'] and v['vector_index_hashes_unchanged']
    replay=json.loads((ROOT/'replay.json').read_text(encoding='utf-8'))
    assert len(replay)==20
    lines=['# 答案引用校验：调整与验证','',
        '已保存到正式问答、混合检索实验、问题拆分实验三个本地Langflow流程。','',
        '## 改了什么','',
        '原检索结果同时连接Parser和“最终答案清理与引用校验”。模型只输出片段编号；程序按与Parser相同的表顺序，从真实页码元数据填写完整范围和章节。','',
        '- 兼容已有的页码引用、多个片段共用括号、全角括号、单元格来源和圆括号编号。',
        '- 缺少完整印刷页码映射时只显示PDF范围，不自动减15。',
        '- 未提供的片段编号显示“引用未核验”，不绑定到其他片段。',
        '- 保留各流程原有think与公式清理行为；清理过程不调用大模型。','',
        '## 验证结果','',
        f'- {v["unit_tests_passed"]}项单元/回归测试通过。',
        '- 旧20题实际答案与各自同次检索表回放通过；原评测和聊天历史保持原样。',
        f'- 最终保存版本实际运行{v["final_saved_flow_live_tests"]}题，覆盖三个流程；另有早期版本跨章和拒答检查。',
        f'- 全部{v["knowledge_count"]}条知识库记录及向量索引文件SHA256保持一致。',
        '- 模型、温度、检索、Parser、入库和网页目标均未修改。只新增证据接线、替换清理节点并调整引用提示规则。','',
        '| 流程 | 测试 | 整题耗时 | 清理节点耗时 |','|---|---|---:|---:|']
    for q in v['live_tests']:
        lines.append(f'| {q["flow"]} | {q["id"]} | {q["elapsed_seconds"]:.2f}秒 | {q["cleaner_seconds"]:.3f}秒 |')
    lines += ['', '这只是几次实际运行的耗时，不是长期性能基准。','',
        f'存储检查边界：变化文件为{v["changed_storage_files"]}。SQLite容器字节变化的具体内部原因本轮未定位；不宣称整个存储目录字节未变。完整分片记录与向量索引字节已分别核对一致。','',
        '## 如何使用','',
        'Langflow中现有三个流程已生效。网页如果仍调用此次更新的正式流程，下一次提问会使用新校验，无需发布前端；本轮没有进行线上网页实测或切换网页目标。旧答案不会自动重写。','',
        '## 仍需区分的边界','',
        '本功能证明“片段编号存在，出处按元数据填写”。它不能判断该片段是否真正支持某个结论，不能为未引用的结论猜配来源，也不能修复检索漏掉某章或模型加强结论的错误。完整片段页码范围不是句子级定位。','',
        '代码和引用示例中的标记不当作真实引用。无法明确绑定片段的其他页码描述只记诊断；本轮最终三次运行没有发现这类描述。','',
        '## 记录与回滚','',
        f'- [20题引用回放]({ROOT/"replay.md"})',
        f'- [验证记录]({ROOT/"verification.json"})',
        f'- [激活记录]({ROOT/"activation.json"})',
        f'- [备份目录]({ROOT/"backups"})',
        '- 回滚脚本：F:/daily/sysarch-fullbook/rollback_citation_validation.py。运行前会核对是否存在后续逻辑修改，防止覆盖新工作。','',
        '## 最终版本实际答案','']
    for q in v['live_tests']:
        lines += [f'### {q["flow"]} · {q["id"]}','',q['question'],'',q['answer'],'']
    (ROOT/'调整与验证.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Report saved:',ROOT/'调整与验证.md')


if __name__=='__main__':main()
