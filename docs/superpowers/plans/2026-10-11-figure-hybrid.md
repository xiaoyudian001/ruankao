# Figure Hybrid Retrieval Implementation Plan

**Goal:** 用户无需图号也能用描述性问题找到有来源的教材原图。
**Architecture:** 图题+同页正文→本地BGE-M3向量；语义/BM25→RRF→已有本地CrossEncoder→最多两张→现有MiniMax图文问答及原图页面。
**Tech Stack:** Python、NumPy、Ollama、已安装本地CrossEncoder、Langflow、现有Sites。
**Execution:** 当前会话逐项执行用户已批准的方案；发布由Sites helper管理提交与打包。

## 1. 索引契约与检索

Create `F:/daily/textbook-bridge/test_figure_hybrid.py`，使用三条不同语义的候选和正交归一化向量：查询与图题零关键词交集时语义候选仍进入融合池；两路命中同ID只保留一次；非法向量拒绝。运行 `python -m unittest discover -s textbook-bridge -p test_figure_hybrid.py`，确认实现缺失失败。

Create `figure_hybrid.py`：`FigureIndex(catalog,vectors)`归一化校验；`candidates(query,vector,limit=8)`调用已有`fuse_rrf`合并实际原记录，保留词法/语义排名。检索文档取caption/chapter/context，最长1800字符；前8候选由`local_rerank_runtime.score_pairs`评分，分数只判断相关性，不作为真实性保证。

## 2. 本机索引构建与校验

Create `build_figure_vectors.py`：批量调用固定127.0.0.1:11434/api/embed，模型bge-m3:latest；写NPZ临时文件后原子替换；清单绑定文档SHA、模型digest、向量SHA、count/dimensions。运行 `python textbook-bridge/build_figure_vectors.py`，检查218条及1024维；同清单再次运行应跳过而非重复嵌入。

加载时验证清单及有限、非零、等维向量，别名摘要变化拒绝继续复用。查询API超时8秒，失败回退旧匹配，重排不下载模型。

## 3. 接入

Modify `figures.py`：保留`select_figures`旧匹配为故障退路，添加精确图号优先及混合选择。`try_enrich_answer`计算一次候选后传入`enrich_answer(...,selected=selected)`，扣除检索耗时并继续现有240秒作业限制。验证无关问题、图号回归和失败保留原答案。

## 4. 真实检查及交付

Create `verify_figure_hybrid.py`：记录真实查询两路候选和本地重排结果，确认自然描述包含图12-2且原书ID/页码不变；对选中的实际原图执行已授权MiniMax问答，确认Web浏览器/Web服务器/数据库与双页码。运行全部连接器测试及现有Node来源校验。

复制实现和设计说明至`docs/local-connector`；构建、Sites helper同步/打包、发布下个版本，正常重启连接器，确认最新云端心跳。浏览器限制不绕过，报告尚未完成的视觉检查。

## 已获得的验证证据

- 本地连接器30项测试通过，包括索引失效、非法向量、图号直查、故障回退与筛选边界。
- 实际生成218条1024维BGE-M3向量，重复构建复用同版本缓存。
- 真实MiniMax图文调用成功采用图12-2，解释浏览器、Web服务器、数据库三层；本地召回与重排约2秒，整次图文验证约37秒。
- 网站生产构建通过；本轮网页展示与API路由未改动，仅接入本地连接器的新检索实现。
- 浏览器视觉复核仍受前次安全限制，未绕过限制，也不作为本轮完成的证据。
