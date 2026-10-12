# Sites / Vinext 框架说明

本项目源于Vinext全栈模板，随后加入软考学习与RAG功能。以下保留原模板的主要开发约定。

## 执行模式

- Node.js最低版本22.13.0，支持Windows、macOS和Linux。
- portable模式保留宿主机HOME、npm缓存、注册表、代理和临时目录配置。
- 仅在`SITES_MANAGED_LINUX_CONTAINER=1`的托管Linux环境选择managed-linux；它依赖Bash、flock、curl、sha256sum及GNU timeout。
- 模式记录在忽略的`.sites-runtime/execution-profile.json`。通过Sites打开或移动源码目录时，使用插件的`configure-execution-profile.mjs`重新设置，不提交该目录。
- `.sites-runtime/`、`.wrangler/`、`.vinext/`是本机运行状态；不用于跨机器复制凭据。

## 运行与安装

`scripts/run-framework.mjs`根据执行模式启动Vinext。portable开发使用Vite热更新，默认5173端口；托管环境预览由平台监督程序管理。

本项目锁文件为`pnpm-lock.yaml`。遵循`package.json`的包管理器版本和`pnpm-workspace.yaml`构建策略。安装与开发依赖应先准备完成；不要并行运行多个依赖安装器。

原模板的`install:ci`保留为环境专用安装入口。当前脚本涉及Linux工具，Windows用户使用主README中的pnpm安装命令。

Sharp默认使用预构建二进制，除非环境明确配置源码编译或全局libvips。脚本将Wrangler和Miniflare状态默认放到项目内部；不要把宿主机系统变量改成项目临时路径。

## Worker与存储

网站Worker使用`vinext/server/fetch-handler`。本项目保留`sites()`构建集成，绑定声明位于`.openai/hosting.json`，不是手工维护的`wrangler.jsonc`。

- `db/index.ts`读取D1绑定，Drizzle管理SQL表结构。
- `cloudflare-env.d.ts`声明DB/BUCKET类型，改变绑定名称时同步调整。
- `pnpm build`生成`dist/server/wrangler.json`。
- `pnpm start`通过Wrangler在本机预览已构建Worker，与开发预览共用`.wrangler/state`，不发布线上。
- 本地预览默认使用占位`Request.cf`元数据，不额外查网络；必要时`CLOUDFLARE_CF_FETCH_ENABLED=true`开启获取。
- 默认关闭Wrangler工具指标；设置`WRANGLER_SEND_METRICS=true`才开启。

## ChatGPT登录

登录后的生产请求由托管平台注入`oai-authenticated-user-id`和`oai-authenticated-user-email`。用户ID适合保存同一站点内的用户数据；邮箱用于显示和所有者检查。

可选完整姓名为UTF-8百分号编码，并通过`oai-authenticated-user-full-name-encoding`说明格式。未提供时退回邮箱。

`app/chatgpt-auth.ts`提供`getChatGPTUser`、`requireChatGPTUser`和登录/退出链接辅助函数。需要登录的服务端页面采用动态渲染。登录必须是顶层导航，不通过fetch/XHR或可能预取的客户端链接发起。

`/signin-with-chatgpt`、`/signout-with-chatgpt`、`/callback`由平台管理，不在应用内实现同名路由，不直接请求AuthAPI授权地址。传入同源相对return_to地址，辅助函数会校验。

平台登录只确认身份。应用的所有者检查、共享范围和各接口数据隔离是独立规则；本项目各模块的实际边界见主README。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `pnpm dev` | 开发服务器与热更新 |
| `pnpm build` | 生成可部署Worker和前端资源 |
| `pnpm start` | 本机预览已构建Worker |
| `pnpm db:generate` | schema变化后生成追加迁移 |

通过Sites发布时以插件的安装、构建、源码同步和发布流程为准。参考：[Vinext](https://github.com/cloudflare/vinext)、[Drizzle D1](https://orm.drizzle.team/docs/get-started/d1-new)。
