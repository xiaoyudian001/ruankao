# Textbook Figures Implementation Plan

**Goal:** 让现有聊天答案使用并展示有出处的教材原图。
**Architecture:** 本机可信图示目录 → 图题关键词/正文页匹配 → 独立视觉Langflow组件 → references_json图文快照 → 现有原页缓存裁剪展示。
**Tech Stack:** Python/PIL/pypdfium2、Langflow/LangChain、MiniMax-M3、React/TypeScript、D1/R2。
**Execution:** 当前会话按任务逐项实施；用户已批准实施和发布。

- [x] 在 textbook-bridge/test_figures.py 和 tests/textbook-figures.test.mjs 先写缺失功能测试：三层图检索、无关问题不匹配、来源/crop边界、未知图id拒绝、旧引用兼容；运行看到失败。
- [x] textbook-bridge/figures.py 实现固定图目录校验、同书catalog、图题检索、实际图片哈希检查、rank追加与视觉prompt/结果校验；build_figure_catalog.py产出本机manifest。通过 Python tests。
- [x] setup_figure_flow.py 复制现有模型配置，创建独立 TextbookFigureAnswer-SysArch，ChatInput以Base64传输参数，model_output连接vision_model；运行真实原图验证。
- [x] lib/textbook/figures.ts 校验每引用最多2图，id为稳定SHA，pdfPage在引用范围内，bbox在0～1；sources.ts保留可选figures并在summary输出安全字段。执行 Node tests。
- [x] bridge.py 在 run_conversation 完成正文之后统一调用图示丰富；未采用图不返回，视觉失败保留正文且说明，不重复视觉生成；备份连接器代码到 docs/local-connector。
- [x] app/textbook/figure-evidence.tsx 复用 source POST/GET 领取原页，受控轮询且卸载取消，裁剪框展示、重试与原页入口；接入 textbook-chat.tsx，历史与移动端兼容。
- [x] 全部Node/Python测试、应用类型检查、真实图问答和浏览器图示/原页闭环、生产构建；Sites helper打包发布，安全重启连接器确认新功能。

## 验证与限制

真实图12-2测试通过（35.59秒）；本地网页接口提交至视觉模型及原页JPEG回传通过（42.61秒）。Node 18项、Python连接器22项、数据库11项、真实路由测试及应用类型检查通过，生产构建成功。浏览器安全策略阻止本地预览，图像在页面中的视觉效果及点击操作未验证，不能宣称已完成浏览器QA。

