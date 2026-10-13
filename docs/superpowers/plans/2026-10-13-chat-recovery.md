# 问答等待与中断恢复实施计划

**目标：** 提交一次问题后，刷新或暂时断网仍可找回同一次任务和结果。

**已确认设计：** 沿用数据库任务与幂等请求编号。页面只保存按账号隔离的当前会话编号和未确认提交的最小请求快照到 sessionStorage；不保存答案、密钥或一般输入草稿。GET 根据所有者校验过的请求编号找回会话。排队／运行时间使用服务端时钟，不伪造检索细分进度。网络读取失败与电脑离线分别显示，保留已有答案和任务。

**技术栈：** React、TypeScript、现有 D1 任务表、Node 原生测试。

## 执行步骤

- [x] 新增 `tests/chat-recovery.test.mjs`：刷新恢复、账号隔离、损坏存储、读取乱序与超时、排队／运行计时。
- [x] 在 `tests/exam-routes.mjs` 增加实际 GET 请求编号恢复断言：本人任务可恢复；他人、案例任务不可恢复；完成后仍可恢复；原 POST 编号重试不会重复插入。
- [x] 运行失败测试：`node --test tests/chat-recovery.test.mjs` 和 `node tests/exam-routes.mjs`，确认新增行为尚未实现。
- [x] 新增 `lib/textbook/chat-recovery.ts`：有效期 24 小时的账号独立记录、同一读取不重叠、切换会话时忽略过期响应、12 秒读取超时。
- [x] 修改 `app/api/textbook/chat/route.ts`：GET 可按 requestId 找回所属会话；返回 selectedSessionId、serverNow、leased_at；保留 owner 与题型限制。
- [x] 新增 `app/textbook/task-progress.tsx`：真实状态、总等待时间、运行时间、等待较久说明、网络恢复说明。
- [x] 修改 `app/textbook/textbook-chat.tsx` 和 `page.tsx`：传入账号标识，提交前保存原请求，读取确认后清理未确认快照；刷新恢复；网络恢复立即 GET；手动重试保持原参数。
- [x] 执行恢复测试、实际 SQLite 路由测试、已有引用与题型测试、类型检查和生产构建。
- [ ] 通过 Sites 官方源代码流程发布；同步 GitHub；报告真实验证结果与浏览器验证范围。

## 边界

不更改模型、检索、知识库、评分逻辑、数据库状态机或超时上限。关闭标签页可能清除 sessionStorage；仍可从服务器最近会话列表回找。自动恢复只读任务，绝不自动重复 POST。此阶段不加入取消任务和流式输出。

## 已验证

25 个纯逻辑测试通过；实际 SQLite 聊天与截图路由检查通过；状态组件和公开演示静态渲染通过；本机预览 `/demo` 返回 HTTP 200。生产构建和本机完整类型检查通过。尚未进行登录后浏览器点击、断网与刷新操作的端到端验证。
