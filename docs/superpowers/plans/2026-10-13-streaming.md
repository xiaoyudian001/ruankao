# 答案增量显示与停止生成 Implementation Plan

**Goal:** 保留现有 RAG 逻辑，打通正文增量显示、停止及残缺答案保存。

**Architecture:** 新增 partial_answer/partial_seq/cancel_requested 字段；bridge progress/control/stop 确认与 owner cancel API 共享 lease 状态。Langflow astream 经可信任务临时邮箱发送已过滤正文；现有网站轮询显示。原有最终校验仍决定正式答案和引用。

**Tech Stack:** TypeScript、D1/Drizzle、React、Python asyncio、Langflow 模型句柄。

## 按顺序执行

- [x] 先写 tests/streaming-routes.mjs 和 textbook-bridge/test_streaming.py；运行确认因缺少增量与停止功能失败。
- [x] lib/textbook/streaming.ts 定义严格快照校验、原子进度/确认 SQL；追加迁移，bridge 增加 progress/control/stopped，chat 增加取消接口及残缺正文查询；验证真实 SQLite。
- [x] textbook-bridge/streaming.py 实现安全标签过滤、临时邮箱及异步取消；single_pass_components.py 对 qa/exam 最终模型调用 astream；LocalFlow 传 UUID/lease，连接器监控快照和停止，不增加模型重试。
- [x] app/textbook/streaming-answer.tsx 展示纯文本临时正文及停止按钮；最终/取消记录切换正确，编辑重生成支持 cancelled，导出明确保留未完成内容。静态渲染验证。
- [x] 同步本机部署脚本，备份并只更新最终生成组件；保持原流程其余节点与模型配置；真实自写问题验证。
- [x] 发布后启动更新连接器，确认心跳。
- [x] 运行相关逻辑、SQLite、Python 生成回归、类型和构建；独立审查，修复必要问题。
- [x] 官方 Sites 打包发布并同步 GitHub；写明实际验证与供应商取消/轮询延迟限制。

命令：node --test tests/answer-actions.test.mjs tests/drafts.test.mjs tests/chat-recovery.test.mjs tests/textbook-*.test.mjs tests/exam.test.mjs tests/screenshots.test.mjs；node tests/streaming-routes.mjs；python -m unittest test_streaming test_answer_generation test_screenshot_generation test_single_pass；node node_modules/typescript/bin/tsc --noEmit；官方 build-site.mjs。

## 完成记录

2026-10-13：Sites 第28版发布成功，应用源码提交6d7fd4299d7af276e87f8fbd212c07ae1629fba0已同步GitHub main。新增0013迁移，本地生成组件及连接器已更新，心跳正常。线上带bridge认证的不存在任务control请求返回409，确认新增接口已生效而不是缺列错误。37项Python生成回归、38项逻辑、5项租约SQL及真实SQLite/界面/类型/构建通过。审查发现的监控关闭阻塞回传P2已修复并复审。真实MiniMax长答案6.05秒首正文、89个快照、46.05秒完成；收到正文后停止样例6.19秒确认。数据仅为生成阶段样例，未执行真实登录浏览器点击测试。
