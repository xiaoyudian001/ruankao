# Review Loop Implementation Plan

**Goal:** 实现用户指定的收藏、复习卡片、主动回忆和计划闭环并发布。
**Architecture:** 复用 owner 和 D1 服务，纯日期调度独立，原问答引用组件复用；客户端收藏只传 jobId，服务器复制快照。
**Tech Stack:** Vinext、React、D1、Drizzle、Node test、SQLite。

## Tasks
- [x] 写入 tests/review.test.mjs，测试上海日期、1/3/7/14 天间隔、重置、卡片长度与非法评分，执行 `node --experimental-strip-types --test tests/review.test.mjs` 确认缺失功能失败。
- [x] 实现 lib/review/model.ts：`scheduleReview(streak, grade, today)`、`studyDate()`、`cardText()`，使上述测试通过。
- [x] db/schema.ts 追加三张表，运行 `node node_modules/drizzle-kit/bin.cjs generate` 并检查 SQL。lib/review/store.ts 定义原子练习 SQL，SQLite 测试幂等及版本冲突。
- [x] /api/textbook/review 实现 owner 检查、同源写入、服务器收藏快照、唯一转卡、卡片编辑及自评并发控制。所有异常保留内容并显示错误。
- [x] /review 实现收藏/卡片/练习/计划，复用 Answer 和 SourcePanel；聊天页加收藏和复习中心入口；首页加今日任务入口。
- [x] 完成类型检查、现有 Node 回归、SQLite 回归、生产构建；通过本地真实页面确认收藏转卡、隐藏/揭晓和计划。
- [ ] 通过 Sites source helper 保存源码和打包；保留 public audience，保存并发布版本，确认成功后报告网址。

## 本次验证
13 项 Node 测试、9 项 SQLite 测试、真实本地 API 幂等/同源/身份/转义检查通过。应用 TypeScript 检查通过；生产构建通过。浏览器已走通收藏、制卡、隐藏答案、揭晓、自评、计划显示。测试样本只写入本地数据库。
