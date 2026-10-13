# 增量显示与停止生成

## 使用

教材问答及真题解析提交后，最终生成阶段的正文会逐步出现；只有模型进入正文输出后才有内容，检索或思考阶段仍显示处理状态。正文每次收到一段更新，网页沿用三秒轮询，不做模拟逐字动画。

生成中的正文尚未完成校验，以纯文本显示，引用不可点击。正式答案经原有来源/题型校验后替换临时正文，开放引用和收藏。

点击“停止生成”：排队任务立即停止；运行任务显示“正在停止”，等待连接器确认。确认后保留已收到正文，并明确标记未完成。可编辑原问题或重新生成；未完成内容不进入后续会话上下文、收藏和练习依据。失败或超时同样保留已到达服务器的正文，Markdown 导出附未完成标识。

## 实现

1. Langflow 最终生成组件使用原有 MiniMax 模型句柄的 astream。只抽取 final_answer；思考区、格式标签、used_figures/practice 等字段不会显示。混合补充保留 AI 通用知识声明。
   当前 Langflow 句柄显式 streaming=False 会让本机 LangChain 的 astream 回退为非流式；对本次答案复制句柄并设置 streaming=True，原句柄及共享模型设置不变。MiniMax 流请求使用 reasoning_split=True 分离正文与思考，不关闭思考能力；该参数见[官方接口说明](https://platform.minimaxi.com/docs/api-reference/text-openai-api)。
2. 生成组件与连接器在当前用户临时目录 ruankao-answer-stream-v1 中共享任务 UUID＋lease 邮箱，只写过滤后正文及停止标记；正常任务结束后清理。实际密钥和检索原文不写入邮箱。
3. 连接器每秒检查一次，变化时推送有序快照；进度无需持续连接到浏览器，网站关闭后任务仍继续。服务器检查 bridge 认证、任务 lease、运行状态、有效期及序号，拒绝终态、过期及陌生租约，忽略乱序快照。
4. 所有者同源取消接口设置 cancel_requested。运行位置保持占用直到 stopped 确认或租约到期；完成更新中也检查取消标记，解决停止与结果竞争。
5. 增量字段由0013追加迁移提供。旧版本连接器仍可一次性提交最终答案；新连接器需要同时更新 streaming.py、bridge.py、single_pass.py、single_pass_components.py 并通过 activate_streaming.py 更新已有生成组件。

## 实际限制

- 网页更新有三秒轮询与网络延迟；正文较短时可能直接看到最终答案。
- 停止当前模型读取会关闭客户端流，但无法保证模型供应商停止服务器计算或不再计费。
- 正在进行的 Langflow 检索/重写无法在这套接口上立即撤销；返回后检查停止标记，不再开始答案生成。
- 临时正文没有最终校验保证，停止后需要重新生成完整答案来核对教材出处。
- 仅聊天 qa/exam 使用增量；案例、论文、点评和截图识别保留原流程。

验证命令：node tests/streaming-routes.mjs；node tests/session-ui-render.mjs；在连接器目录执行 python -m unittest test_streaming test_answer_generation test_screenshot_generation test_single_pass test_qa_fallback。真实模型自写资料测试用 verify_streaming.py，结果记录于本机 output，测试不会新增正式学习会话。

## 本机实测（2026-10-13）

自写缓存资料长答案：从生成调用开始6.05秒看到正文，46.05秒完成，观察到89个正文快照，最终2917字符。另一请求收到正文后主动停止，6.19秒返回停止确认并保留已有6字符。该耗时不包括教材检索，不能当作所有问题的速度保证。37项Python生成相关测试、38项已有逻辑测试、SQLite取消/完成竞争和会话/截图路由、界面静态渲染、类型与生产构建通过；未执行真实登录浏览器的点击测试。
