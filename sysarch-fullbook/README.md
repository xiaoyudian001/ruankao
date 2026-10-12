# 教材处理与RAG检索源码

本目录保存已实现的教材解析、缓存清理、分片入库、页码映射、混合检索、问题规划、重排、多轮追问和引用处理代码。原PDF、OCR全文、向量、模型、真实Langflow流程导出与运行进度需在本机另行准备。

## 模块

| 范围 | 主要文件 |
| --- | --- |
| PDF解析、清理与分片 | `parse_book.py`、`core.py`、`watermark_cleanup.py`、`run_fullbook.py` |
| 分批入库与API | `batch_reader_component.py`、`langflow_api.py`、`setup_langflow.py` |
| 双页码与来源 | `printed_page_mapping.py`、`citation_format.py`、`source_references.py` |
| BM25与RRF | `hybrid_retrieval.py`、`hybrid_components.py` |
| 复杂问题与子查询 | `complete_retrieval.py`、`subquery_retrieval.py` |
| 父级上下文 | `parent_context.py`、`build_parent_context.py` |
| 本地CrossEncoder | `local_rerank_runtime.py`、`rerank_retrieval.py` |
| 多轮追问 | `conversation_rewrite.py`、`conversation_components.py` |
| 输出与引用校验 | `answer_citations.py`、`citation_validation_component.py` |

当前部署的正式知识库是`SysArchTutorRAGv3`；有些早期脚本默认V2，这是迁移历史，运行前应核对目标。当前问答使用核对后的教材印刷页码和PDF物理页码，没有印刷页码的页面保留物理页序。

清理合并排版造成的中文词内空格和断行，同时保留英文单词间空格。跨页段落切片保留来源范围，分片ID用于去重和恢复。水印处理采用保守规则，无法确认的专业名词、数字和公式不由常识自动改写。

部分脚本包含现有部署的`F:/daily`路径、教材哈希与Langflow流程ID。`activate_*`、`rollback_*`、`setup_*`及全书入库脚本可能修改本地流程、数据或配置，使用前应明确目标并保留自己的备份。仓库源码不等同于现有知识库备份。

测试、评估和验证脚本分开保存。`test_*.py`用于规则测试；真实验证及评估需要教材、索引和模型服务。完整部署边界见[运行说明](../docs/setup.zh-CN.md)，对外已实现能力见[功能清单](../docs/features.zh-CN.md)。
