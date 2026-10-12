# Screenshot Question Implementation Plan

> Inline Execution: 通过executing-plans逐项执行；用户已批准功能和发布，Sites helper负责源码提交与推送。

**Goal:** 截图经核对后调用图文真题解析，保留原题图表。

**Architecture:** 私有R2图片 + 同一个jobs队列内部recognize任务 + 受有效lease约束的桥接图片读取。确认的识别任务id绑定exam任务，生成时独立携带questionImages，不充当教材引用。

**Tech Stack:** React/Vinext、D1/Drizzle、R2、Python、Langflow、MiniMax。

### 1. 契约
- [x] tests/screenshots.test.mjs验证PNG魔数/尺寸、体积、manifest、recognition字段；Python test_screenshots.py验证识别标签、不提前作答、图文传递和普通问答兼容。运行缺模块失败后实现lib/textbook/screenshots.ts与textbook-bridge/screenshots.py。
- [x] schema添加screenshot_json、recognition_json、screenshot_ready，使用Drizzle追加迁移。

### 2. 私有上传与队列
- [x] app/api/textbook/screenshots/route.ts实现POST multipart（requestId及images），GET任务与私有图片；bridge新增screenshotRead/recognitionComplete有效lease操作。CLAIM携带screenshot_json，普通聊天和历史排除recognize；chat验证已完成本人识别manifest，幂等比较截图id。
- [x] SQLite实际路由测试覆盖上传失败不留错误记录、所有权、图片类型、队列限制、lease、重试和图文exam关联。

### 3. 本地图文
- [x] generation_code区分recognize/exam；识别仅转录标签，exam携带questionImages与最多两张教材原页。bridge领取后按lease从云取图并校验，识别结果交付；图文不可用时直接失败，禁止丢失原题图片的静默降级。
- [x] setup_single_pass同步伴随组件，保持原问答流程指纹；57项现有测试和新契约测试通过。

### 4. 网页
- [x] screenshot-input.tsx集中图片规范化、预览、上传识别轮询、注意事项和确认。textbook-chat接收识别文本和attachment状态，锁定识别期间会话变更，确认后提交图片关联，成功清空、失败保留；旧图文题支持回看与重试。
- [x] React SSR确认有上传/确认入口，应用TypeScript、生产构建通过。

### 5. 验证发布
- [x] 合成架构师职责选择题截图经真实MiniMax识别，改动识别文字后图文解析仍携带原图、一次生成及有效教材引用；练习沿用可选结果契约。
- [ ] 镜像安全连接器源文件；官方Sites helper推送打包，save/deploy保持public；安全重启连接器确认screenshot_ready和心跳。

