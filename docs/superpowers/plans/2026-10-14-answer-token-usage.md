# 答案 Token 用量实施计划

**目标：** 已完成聊天答案展示模型实际返回的答案生成用量并发布。

**架构：** 模型响应保留 usage，逐次答案生成合并已知用量；连接器提交可选 tokenUsage，D1 保存可空 token_usage_json，历史查询返回经过验证的对象，网页显示紧凑统计与可展开详情。证据判断、问题重写、规划排除；统计缺失明确标注。

**技术：** Python、LangChain、Langflow 自定义组件、TypeScript、React、D1 SQLite、Sites。

## 执行步骤

- [ ] 先添加 Python 回归测试：响应元数据、流式最终累计、缺失统计、格式重试、回退；验证失败后实现 textbook-bridge/token_usage.py 并集成 streaming.py、single_pass_components.py、bridge.py、single_pass.py。
- [ ] 添加 TypeScript 统计验证测试和实际路由 SQLite 用例；验证失败后实现 lib/textbook/token-usage.ts，更新完成 SQL、桥接 POST、历史 GET 和 db/schema.ts，生成追加迁移。
- [ ] 添加 React 静态渲染用例；验证失败后实现独立 answer-usage.tsx 并接入聊天标题。
- [ ] 运行 Python 用例、Node 路由和渲染测试、TypeScript 编译与生产构建。检查迁移、取消竞态和旧客户端兼容。
- [ ] 代码审查，解决关键发现。只更新现有生成组件的统计代码与连接器文件，保留所有节点及连线；备份并实测编码证据调用的真实用量。
- [ ] 使用 Sites 源码辅助工具提交、构建、打包并发布相同来源。确认生产迁移与新记录统计；同步 GitHub，记录版本和验证限制。

## 关键测试数据

1. usage_metadata={input_tokens:4800,output_tokens:506,total_tokens:5306} 保存为整数；负数、布尔、字符串拒绝。
2. 流式两条累计报告采用最后完整报告，不相加；一个调用仍计 reportedCalls=1。
3. 格式失败后成功的两次报告相加。图文失败没有用量时，正文回退的统计标记 unreportedCalls>=1。
4. 无模型调用的澄清和旧记录 tokenUsage=null；真实零输出值允许。
5. 完成后的会话刷新保留统计；错误租约、过期任务和取消任务不会写入最终统计。

## 验证命令

Python 使用 Langflow 虚拟环境，设置 PYTHONPATH 包含本检出 textbook-bridge 和 F:/daily/sysarch-fullbook 后运行 unittest。Node 使用 E:/tools/node22/node.exe --experimental-strip-types 执行 tests/token-usage.test.mjs、tests/token-usage-routes.mjs、tests/token-usage-render.mjs；相关现有测试同样执行。构建使用 Sites build-site.mjs。
