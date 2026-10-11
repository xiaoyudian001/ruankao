# 教材问答一次生成 Implementation Plan

**Goal:** 减少表格/公式问题的重复答案生成，并保留引用、回退和阶段耗时。
**Architecture:** 已有检索链复制为检索伴随流程，返回本次来源与提示；连接器先准备视觉证据，再选文本或图文句柄生成一次答案。
**Tech Stack:** Python、Langflow、原MiniMax配置、本地检索/重排、Sites。
**Execution:** 当前会话按已批准设计逐项执行；Sites helper管理提交和发布，不分派子代理。

## 1. 路由测试

- [x] 创建`F:/daily/textbook-bridge/test_single_pass.py`，运行`python -m unittest test_single_pass`：六项因路由文件缺失失败。
- [x] 实现`single_pass.py`，方法`run_single_pass(local,job,budget=220)`。严格流程为`prepare_conversation → retrieve_evidence → prepare_visual → generate_evidence`。模型调用数由调用前递增，图文失败才允许零图正文回退。
- [x] 执行`python -m unittest discover -p 'test*.py'`确认新路径次数、澄清、原页故障和未采用图片逻辑，以及原历史转义测试通过。

## 2. 拆出检索与生成

- [x] 新建`single_pass_components.py`。EvidenceSnapshot接受原父级表与原提示模板，输出`rows/references/textPrompt`。SingleEvidenceAnswer接受base64JSON和文本/图文两个句柄，只调用选用的`.ainvoke`；沿用`serialize_visual_result`。
- [x] 新建`setup_single_pass.py`。复制default/complete检索链，移除LanguageModel、FinalAnswerCleaner、ChatOutput，保留完整模式规划句柄。连接父级表和Prompt到EvidenceSnapshot。新生成流程复用原文本和图文模型值。保存`single-pass-flows.json`；用原逻辑指纹验证原流程未修改。
- [x] `bridge.py`增加问题处理、检索及生成方法；新就绪检查通过后网页任务用`run_single_pass`。旧`run_conversation`仍用于原流程验证，不能在正常新路径中调用。

## 3. 耗时、契约与真实验证

- [x] `figures.py`、`figure_hybrid.py`、`structured.py`为视觉检索/重排/原页准备提供可选timings字典。连接器结果送云端前移除本地timings并写本机`stage-timings.ndjson`。
- [x] 新建`verify_single_pass.py`，实测v18同一可用性公式、表2-2及续表问题，再查普通职责及完整检索追问。保存答案与分阶段耗时到固定output目录；确认每项正常答案生成计数为1、原页编号与引用存在。
- [x] Node网页来源契约检查通过。源码镜像和说明写入现有站点docs，构建输入未改时复用成功产物。

## 4. 发布与切换

- [ ] 官方Sites helper打开源码、同步并打包，保存版本后部署；保持原公开访问策略。
- [ ] 平稳重启连接器，确认`single_pass_ready`及云端心跳正常。记录最终部署和验证；说明浏览器视觉检查受已有策略限制。