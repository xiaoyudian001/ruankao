# 真题解析 Implementation Plan

> Inline Execution: 使用executing-plans在当前会话逐项执行；用户已批准功能与接入发布。

**Goal:** 聊天页完成文字真题解析与先答后看的类似单选练习。

**Architecture:** 在现有job/桥接队列上新增qa/exam类型；复用v19检索快照及一次生成模型。练习答案保存在D1，GET按已提交状态裁剪字段；客户端提交选项后读取已保存结果。

**Tech Stack:** React/Vinext、D1/Drizzle、Python连接器、Langflow、MiniMax。

### 1. 契约与验证
- [x] 增加tests/exam.test.mjs和textbook-bridge/test_exam.py，先验证模块缺失/功能失败。
- [x] 实现lib/textbook/exam.ts及textbook-bridge/exam.py。parsePractice(value,ranks)校验四个A-D选项、唯一正确项、有效来源；practiceView(result,choice)提交前仅返回question/options。Python生成标签<final_answer>、<used_figures>、<practice>由serialize_generation严格解析。

### 2. 入队、保存与练习提交
- [x] db/schema.ts追加task_type默认qa、exam_json、practice_choice、exam_ready默认0；执行node node_modules/drizzle-kit/bin.cjs generate并检查新迁移。
- [x] chat route验证taskType、按类型幂等、过滤练习隐藏字段；bridge claim传task_type，complete校验exam结果；exam POST用UPDATE … WHERE practice_choice IS NULL保存首个选项，拒绝更换答案；通过真实路由SQLite检查所有者、来源、重读与隐藏。

### 3. 模型与网页
- [x] single_pass.py识别exam独立检索，并传递练习结果；bridge.generate_evidence传taskType并解析结构化结果；generation_code在exam分支使用受限解析提示。setup_single_pass更新现有伴随生成节点并检查原流程指纹。
- [x] 新增app/textbook/exam-practice.tsx；聊天页增加类型切换、解析标签、题目输入样例、提交练习、刷新读取结果、错误重试保持原类型。不改常规来源侧栏与收藏。

### 4. 验证发布
- [x] Python新增契约/路由测试与原50项测试、Node新增契约/SQLite路由测试；真实架构设计师职责四选一题检索生成，检查引用与一次调用。
- [ ] 检查真实模型结果通过服务端练习契约；TypeScript及Sites build成功后helper同步源码打包，save/deploy正式版本。
- [ ] 安全停止并隐藏重启连接器，验证exam_ready与连接心跳，记录发布结果和验证限制。

