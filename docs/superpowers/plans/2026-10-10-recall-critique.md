# Recall Critique Implementation Plan

**Goal:** 发布教材依据的可选 AI 回忆点评并接通本机模型。
**Architecture:** 独立 D1 点评任务队列，由已认证 outbound bridge 领取，独立 Langflow MiniMax 组件结构化输出；自评记录关联任务。
**Tech Stack:** Vinext / D1 / React / Python / Langflow。

- [x] tests/critique.test.mjs 与本机 test_critique.py 先验证：合法引用接受，越界/空引用拒绝，带换行引号回忆JSON不丢失；运行确认缺失实现失败。
- [x] lib/review/critique.ts 结构校验，db/schema.ts 新队列及自评关联字段，drizzle-kit generate 只追加迁移。
- [x] app/api/textbook/critique/route.ts 本人快照、幂等与任务状态；lib/review/critique-server.ts 原子领取完成及过期；桥接端 heartbeats 宣告能力。
- [x] F:/daily/textbook-bridge/critique.py 与独立 Langflow 配置脚本实现模型调用；不改已有问答流程。运行真实已知教材样本确认依据与遗漏。
- [x] app/review/critique-panel.tsx 请求/轮询/引用，review-center.tsx 自评关联与历史展示；失败允许继续自评。
- [x] Node/Python/应用类型检查、真实本地 API 与浏览器闭环验证、生产构建。

- [ ] 用 Sites helper 打包并发布，重启桥接确认心跳能力。

