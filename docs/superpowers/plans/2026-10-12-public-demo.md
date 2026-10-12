# 公开演示 Implementation Plan

> **For agentic workers:** 按顺序在当前会话执行；用户已确认实施，不重复询问执行方式。

**Goal:** 让新访客无需登录或电脑在线即可体验三个完整预录学习场景。

**Architecture:** `/demo`独立公开路由，固定自写资料，React本地状态控制场景、示例稿和点评。复用只负责文本显示的Answer，引用打开独立的样例原页区。README展示与实际能力保持一致。

**Tech Stack:** TypeScript、React、Vinext、Tailwind；Node测试及React静态渲染。

## Task 1: 验收先行

- [x] 新建 `tests/demo-render.mjs`，转译组件并验证三个场景、提交前隐藏点评、两稿不同反馈、引用原页和可关闭区域。
- [x] 执行 `node tests/demo-render.mjs`，确认缺少公开演示时失败。

## Task 2: 固定样例与公开页面

- [x] 新建 `lib/demo/content.ts`，提供三份自写来源、问答、案例两稿、论文提纲与两稿点评。内容必须明确为演示，事实不足不补造结果。
- [x] 新建 `app/demo/page.tsx`、`app/demo/demo-workspace.tsx`，公开首屏、切换按钮、案例提交、论文比较、可关闭来源区；不依赖私有API。
- [x] 首页追加 `/demo` 链接，不改已有学习入口权限。
- [x] 重跑渲染检查；执行全部Node契约及TypeScript检查，解决实际失败。

## Task 3: 对外介绍与发布

- [x] 新建 `public/demo/overview.svg` 作为演示路线示意；重写README首屏并提供简洁英文简介，新增公开演示说明。
- [x] 修正运行文档迁移范围，保留绝对路径、流程导入、Python依赖的实际限制；不承诺完整自动部署。
- [ ] 执行官方Sites构建，确认 `/demo` 路由；用官方源码工作流推送、打包、保存、部署现有站点。
- [ ] 检查GitHub目标分支与远端状态后普通推送。保存外部完成记录，说明浏览器验证边界。
