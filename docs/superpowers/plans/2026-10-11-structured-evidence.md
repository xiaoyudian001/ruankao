# 教材表格与公式问答 Implementation Plan

**Goal:** 现有问答能够对照原教材表格和公式解释、计算，并保留可核查双页码。
**Architecture:** 已解析页面→独立表格/公式记录→本机BGE-M3/BM25/RRF/重排→最多2原页→已有MiniMax图文流程→现有聊天引用与原页展示。
**Tech Stack:** Python、NumPy、Ollama、PDFium、已有本地CrossEncoder、Langflow、Sites。
**Execution:** 在当前会话按用户已批准的方案执行；Sites helper负责提交同步与打包。

## 1. 来源索引

- [x] 在`F:/daily/textbook-bridge/test_structured.py`先验证Markdown行列完整保留、未解码公式没有伪造文本、识别独立A=MTBF/(MTBF+MTTR)、精确表号与无关问题；运行`python -m unittest test_structured`确认缺少实现失败。
- [x] `structured.py`实现`table_blocks(text)`、`formula_lines(text)`、`question_kinds(query)`、`select_structured(query,refs,catalog=None)`；明确表号用`表\s*(\d+)\s*[-－—]\s*(\d+)`匹配真实标题。用原页、kind、教材SHA生成稳定ID。
- [x] `build_structured_catalog.py`逐页加载清理Markdown及原解析标记，关联page-map与章节；保存`output/sysarch-structured-rag/catalog.json`，不得填补未识别公式。

## 2. 本地混合检索与原页

- [x] `build_structured_vectors.py`批量8条调用现有`embeddings`，保存NPZ及绑定catalog/doc/model/vector SHA的清单；218张图的索引与正文库不变。
- [x] `structured.py`使用现有`FigureIndex`、`bounded_rerank`和同来源RRF；按问题kind筛选后最多2页，优先真实表号。索引坏或模型故障时用相同catalog的BM25及正文页交集回退，不能从浏览器指定任意图片路径。
- [x] `materialize(records)`仅使用固定本机PageRenderer，原页PNG保存到固定结构证据目录；SHA绑定后送给MiniMax，bbox固定完整原页，避免伪造区域。

## 3. 接入与契约

- [x] 修改`figures.py`：表格/公式选择优先，兼容原架构图检索，共享两图上限。原图路径白名单扩充固定结构图片目录；MiniMax指令包含表格行列、公式符号、统一单位和明确标注的例子。更新既有Langflow图文节点，不另建模型配置。
- [x] `lib/textbook/figures.ts`增加可选kind，允许figure/table/formula，旧记录保持兼容，非法kind拒绝；网页原图卡片使用相应类型文字。不改页面导航和受保护的原页API。
- [x] 来源契约新增测试，运行连接器测试与Node来源测试，生产构建。

## 4. 实测与发布

- [x] 渲染并查看PDF323、628、55、56页；真实测试可用性计算与表格权限归属，保存来源与答案证据，不保存凭据。
- [x] 同步代码说明到`docs/local-connector`，报告浏览器视觉检查限制。`Sites`发布及本机切换由本次部署状态和连接器`status.json`记录。
