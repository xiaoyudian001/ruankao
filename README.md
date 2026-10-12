# 软考 40 天冲刺

## 本次新增：论文写作训练

新增 `/essays`：保存真实项目经历，生成切题提纲，按五个段落写作与点评，修改后再次提交，并保留材料与原稿快照。详见[论文训练说明](docs/essay-training.zh-CN.md)。

## 多题型解析与案例逐问练习

题目解析现在按选择、问答、案例、计算、判断、填空等实际题型组织答案。新增 `/cases` 案例练习：共享背景、逐问先答后看、教材依据点评、蓝色出处引用及修改后再次点评。详细操作与机制见[案例练习说明](docs/case-study.zh-CN.md)。

面向系统架构设计师备考的学习工作台，将教材检索、图文问答、题目解析和主动回忆练习接到同一个网页中。

- **在线地址**：[复习总览](https://ruankao-40-day.xiaoydian.chatgpt.site/) · [教材问答](https://ruankao-40-day.xiaoydian.chatgpt.site/textbook) · [复习中心](https://ruankao-40-day.xiaoydian.chatgpt.site/review)
- **功能基线**：已发布的网站第 21 版，更新于 2026-10-12。
- **回答模型**：沿用本机 Langflow 配置的 MiniMax-M3。ChatGPT 登录负责身份验证，教材答案由 MiniMax 生成。
- **部署方式**：网页和学习记录运行在云端；教材、向量库与检索流程运行在本机。电脑联网并启动连接器后，可以在网页中发起新的问答。

## 已实现的功能

| 模块 | 当前能力 |
| --- | --- |
| 40 天复习总览 | 六阶段复习路线、每日打卡、学习时长与刷题数统计、今日卡片复习任务 |
| 资料管理 | 上传、分类、下载和删除学习资料，单文件上限 25 MB |
| 教材问答 | 从教材检索证据，生成解释、例子及可点击的片段引用 |
| 完整检索实验 | 按需拆分复杂问题，语义召回与 BM25 关键词召回，经 RRF 融合、本地重排和上下文扩展后作答 |
| 多轮追问 | 使用同一会话最近 3 轮已完成问答补全追问；无法确定对象时请求澄清 |
| 来源核对 | 同时显示教材印刷页码与 PDF 物理页码；蓝色引用打开原页及检索文本，侧栏支持返回聊天 |
| 教材图文问答 | 按图号或描述检索架构图、流程图，以及相关表格、公式原页；只展示模型实际采用的教材原页 |
| 文字题解析 | 粘贴题干及选项，查看答案、解题思路、逐项解释和教材依据 |
| 截图识题 | 上传或粘贴同一道题的最多两张截图；先核对识别文字，再携带原图解析 |
| 类似练习 | 原题解析后按证据生成一道辅助单选题；提交选项后才显示答案和解析，刷新保留作答结果 |
| 答案收藏 | 保存回答与来源快照，制作可编辑的问答卡片 |
| 主动回忆 | 先自行作答，再揭晓参考答案并自评；按 1、3、7、14 天间隔安排复习 |
| AI 回忆点评 | 基于原收藏的教材证据说明答对、遗漏和需要纠正的内容，保存点评记录 |

详细范围和限制见 [功能清单](docs/features.zh-CN.md)。案例逐问训练已实现；按官方评分细则精确计分尚未实现；论文提纲与分段写作训练已实现。

## 三个常用入口

### 教材问答

进入 `/textbook`，选择“教材问答”，输入完整问题。可选择“当前问答”或“完整检索实验”。答案中的片段引用可打开原 PDF 页核对。

同会话支持追问，例如先问“什么是 MTBF”，再问“它与 MTTR 有什么区别”。新建会话会清空追问上下文。检索问题可在答案下方展开查看。

### 真题解析与截图识题

1. 选择“真题解析”，粘贴题干、小问及必要条件（选择题附全部选项）；也可上传或粘贴 PNG、JPEG、WebP 截图。
2. 图片输入一次只处理一道题，最多两张。浏览器转为 PNG，每张转换后不超过 2 MB。
3. 点击“识别题目”，检查输入框中的文字，尤其是否定词、数字、公式和选项。
4. 点击“我已核对文字，保留原图解析”，再发送。原题图表会随经核对的文字一起进入图文模型。
5. 查看解析与教材引用；有类似练习时，先选择选项，再提交查看解释。

原题截图可从历史回答中的“查看原题截图”回看。没有提供标准答案时，原题答案属于模型判断；生成的类似题是 AI 辅助练习，不是历年真题。

### 复习闭环

`答案收藏 → 复习卡片 → 主动回忆 → 自评或 AI 点评 → 40 天复习计划`

收藏内容与卡片存储在 D1。已保存的内容和自评练习可以在电脑离线时查看；新问答、AI 点评和未缓存的原页仍需要本机服务在线。

## 实现机制

### 问答链路

`网页提交问题 → 云端任务队列 → 本机连接器领取 → Langflow 检索证据 → MiniMax 生成答案 → 校验引用并清理输出 → 云端保存 → 网页显示`

- **向量化**：Ollama 的 `bge-m3:latest` 在本机生成文本向量。
- **向量库**：Langflow 管理的 Chroma Local 知识库；当前教材库为 `SysArchTutorRAGv3`。
- **混合检索**：完整模式结合语义检索与 BM25，用 RRF 合并排名，再通过本地 CrossEncoder 重排。
- **重排模型**：`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`，从本机模型目录加载。
- **答案生成**：正文和图文使用同一供应商 MiniMax；通常最终答案生成一次。追问重写、复杂问题规划是独立步骤，可能额外调用模型。
- **图像预算**：每轮最多两张教材原页；截图题另支持最多两张用户原题截图。原题截图不充当教材引用。
- **页码来源**：程序维护页码元数据，模型不能自行推算页码。跨页分片保留完整来源范围。

图示索引使用图题、章节和同页正文的文本向量，不能等同于将原图像素直接写入向量库。模型实际读取图片发生在相关原页被选中之后。

### 连接方式

连接器只主动向固定网站发起 HTTPS 请求。本项目没有把本机 Langflow 或 Ollama 的端口直接公开到互联网。

队列使用任务类型、领取租约和过期检查；问答、截图识别与点评共享任务互斥规则。回传失败只重试结果交付，避免因网络重试重复生成答案。截图只能由所有者读取，本机桥接只能在有效任务租约内取得对应原图。

详细说明见 [本机运行与部署](docs/setup.zh-CN.md) 及 [一次答案生成](docs/local-connector/single-answer.md)。

## 技术栈

| 部分 | 使用的工具 |
| --- | --- |
| 网页 | TypeScript、React、Vinext、Vite、Tailwind CSS |
| 云端运行 | Cloudflare Workers，由 Sites 发布 |
| 结构化数据 | Cloudflare D1、Drizzle ORM |
| 文件存储 | Cloudflare R2 |
| 流程编排 | IBM Langflow Desktop |
| 嵌入与检索 | Ollama BGE-M3、Chroma Local、BM25、RRF |
| 本地重排 | Transformers / PyTorch CrossEncoder |
| 文档处理 | Docling、RapidOCR、PDF 渲染与清理脚本 |
| 回答和图文识别 | MiniMax-M3 |
| 本机连接 | Python、Windows PowerShell、DPAPI 加密配置 |

## 源码目录

```text
app/                    网页、聊天、复习中心与 API
lib/textbook/           问答、来源、题目、截图等数据契约
lib/review/             卡片排期、复习与点评逻辑
db/                     Drizzle 表结构
drizzle/                按顺序追加的数据库迁移
textbook-bridge/        本机连接、图文生成、流程设置与验证源码
sysarch-fullbook/       教材解析、清理、检索、重排和引用处理源码
docs/local-connector/   各阶段实现说明与连接器源码快照
docs/superpowers/       功能设计及实施记录
scripts/                前端运行和构建脚本
tests/                  网页契约、实际路由适配及数据库测试
```

本仓库保存源码，不包含原教材、OCR 全文、向量数据、模型权重、用户上传截图、学习记录或真实密钥。部分本机脚本保留当前部署的 Windows 路径和流程 ID；换机器时需要核对配置，克隆仓库不会自动得到现有 Langflow 流程、知识库或云端数据。

## 前端开发

需要 Node.js `>=22.13.0`，以及与 `package.json` 中 `packageManager` 一致的 pnpm。

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

默认开发端口为 `5173`。干净克隆默认使用 portable 执行模式；项目不要求为 Windows 前端开发安装 Bash。`install:ci` 是保留的环境专用脚本，不是 Windows 快速开始入口。

```powershell
pnpm build
pnpm start
```

构建后 `pnpm start` 使用 Wrangler 在本机预览 Worker，不会发布到线上。完整的登录、D1/R2 配置和迁移步骤见 [运行说明](docs/setup.zh-CN.md)。

原始 Sites/Vinext 模板的运行约定见 [框架说明](docs/framework.zh-CN.md)。

## 验证

以下命令在项目根目录运行，主要检查数据契约和本地适配器，不会自动把题目写入生产会话：

```powershell
node --experimental-strip-types --test tests/*.test.mjs
node tests/exam-routes.mjs
node tests/screenshot-routes.mjs
node tests/critique-routes.mjs
node tests/exam-render.mjs
node tests/screenshot-render.mjs
python -m unittest discover -s tests -p 'test_*.py'
```

本机连接器测试在准备了 Python 依赖的环境中运行：

```powershell
python -m unittest discover -s textbook-bridge -p 'test*.py'
```

真实模型验证脚本会调用现有 MiniMax 服务；运行前应核对输入、配置和模型费用。教材相关验证需要本机自备教材及索引。本次连接器73项检查中68项通过，5项因公开源码不含私有教材图示目录而跳过。传输测试使用临时模拟流程清单，不需要真实密钥。通过样例不能保证所有题目或所有教材公式都能正确识别。浏览器完整交互验证尚未完成。

## 当前边界

- 新答案依赖电脑联网、连接器、Langflow 和 Ollama；开机自动启动发生在用户登录 Windows 后。
- 当前复习日历的起始日期和考试日期写在源码中，换考试周期需要调整，页面日期不代表官方考试公告。
- 教材问答、截图和复习模块有所有者及同源检查；首页打卡和资料接口目前是单套共享数据，尚未实现多用户隔离。
- 长续表、看不清的公式、缺少选项的题目需要人工核对。无有效证据时不保证生成类似练习。
- 用户原题图文会发送给配置的 MiniMax 服务；教材正文向量化和本地重排在本机完成。
- 项目未单独声明开源许可证。第三方组件的许可证保留在相应目录；教材、模型权重及第三方服务的使用条件应分别确认。

## 相关文档

- [功能清单](docs/features.zh-CN.md)
- [本机运行与部署](docs/setup.zh-CN.md)
- [框架说明](docs/framework.zh-CN.md)
- [原图问答](docs/local-connector/figures.md)
- [表格与公式问答](docs/local-connector/structured.md)
- [真题解析](docs/local-connector/exam-analysis.md)
- [截图识题](docs/local-connector/screenshots.md)
