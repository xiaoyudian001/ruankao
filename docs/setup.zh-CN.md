# 本机运行、配置与部署

## 1. 组成

网页运行在Cloudflare Worker，D1保存记录和队列，R2保存资料、原页缓存及题目截图。本机Python连接器通过出站HTTPS领取任务，调用本机Langflow和Ollama，再交付结果。

这份源码对应当前实例，不是全自动安装器。真实Langflow流程JSON、MiniMax密钥、Chroma集合、教材和索引不进入GitHub仓库。

## 2. 前端

安装Node.js `>=22.13.0`及`package.json`指定的pnpm。项目根目录执行：

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

默认地址为`http://localhost:5173`。可用`pnpm dev -- --port 5174`调整端口。开发服务只绑定本机；避免同一目录重复启动。

没有忽略的执行配置时默认portable模式。portable模式仅在本机开发请求上模拟ChatGPT登录：打开`/signin-with-chatgpt?return_to=/`，开发身份为`seedy@sites.test`；教材接口仍要求匹配`RAG_OWNER_EMAIL`，因此本地调试需要单独设置开发所有者。模拟登录不进入生产构建。

构建与预览：

```powershell
pnpm build
pnpm start
```

`pnpm start`仅预览已构建Worker，不部署；服务地址以终端为准。必要时`pnpm start -- --port 8788`。

## 3. 站点运行配置

`.openai/hosting.json`保留站点身份和绑定名称：D1为`DB`，R2为`BUCKET`。已有站点更新应保留其project_id；创建独立部署时应通过对应平台注册自己的站点。

| 服务端配置 | 用途 |
| --- | --- |
| `RAG_BRIDGE_SECRET` | 验证本机连接器，必须与本机解密后的连接密钥一致 |
| `RAG_OWNER_EMAIL` | 教材问答与复习模块的所有者账号 |
| `RAG_SITE_ORIGIN` | 验证浏览器写请求的同源地址 |
| `DB` / `BUCKET` | 数据库与对象存储绑定 |

配置通过部署平台设置。本机开发变量可保存在已忽略的`.dev.vars`；不要放入README、源码常量或前端环境变量。

## 4. 数据库迁移

表结构位于`db/schema.ts`，已有迁移从0000到0013。0007加入真题解析，0008加入截图识别，0009加入案例练习，0010加入论文训练，0011加入历史会话删除标记，0012加入编辑／重新生成的原问题关联，0013加入增量正文及停止请求；旧迁移保持不变。公开演示本身不依赖数据库。

修改schema后：

```powershell
pnpm db:generate
pnpm build
```

本地预览需按顺序应用尚未执行的迁移。例如：

```powershell
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_ancient_vulture.sql
```

替换为实际未执行的文件，不重放已经应用的SQL。`.wrangler/state`是本地状态；Sites发布时由平台应用线上迁移，本地迁移不能代表线上已迁移。

## 5. 教材与模型

当前实例使用以下配置：

- Langflow API：`http://127.0.0.1:7860/api/v1`。
- Ollama API：`http://127.0.0.1:11434`，模型`bge-m3:latest`。
- 知识库：`SysArchTutorRAGv3`，Chroma Local。
- MiniMax-M3：在Langflow内配置，正文温度0.2、图文及点评温度0.1。
- 本地重排：`mmarco-mMiniLMv2-L12-H384-v1`，从已核对的本机模型目录离线加载。
- 教材来源：部署实例的PDF哈希、页数和页码映射由脚本检查。

本机源码分成相邻的`textbook-bridge/`和`sysarch-fullbook/`两个目录。现有脚本还包含`F:/daily`等绝对路径，部分默认知识库名和流程ID固定。迁移到新机器时逐项核对这些路径、模型目录与流程ID；不要直接在他人的Langflow环境执行activate/rollback脚本。

Python依赖由相应部署环境提供，涉及Docling/RapidOCR、NumPy、Pillow、PDF渲染、PyTorch及Transformers。本仓库未提供经新机器完整复现验证的Python依赖锁文件。

先准备教材解析缓存及来源映射，再建立混合检索/重排配置，最后运行图示、结构原页和一次生成入口设置脚本。各setup脚本依赖已有基础流程，并不会从空Langflow实例自动创建整个系统。

## 6. 本机连接器

现有Windows启动脚本读取本机`config.json`的站点地址、Python路径和DPAPI加密密钥，解密后经隐藏标准输入交给连接器。真实文件不纳入仓库。

已配置实例的手动启动和停止：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File F:\daily\textbook-bridge\start.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File F:\daily\textbook-bridge\stop.ps1
```

启动脚本中的Langflow/Ollama可执行文件路径也需要按机器调整。自动启动通过当前用户Windows启动文件夹快捷方式实现，发生在用户登录后。

`status.json`记录连接和能力状态，包括`connected`、`exam_ready`、`screenshot_ready`等；`bridge.log`记录事件。启动后的图示重排预热可能需要时间。正常停止等待当前任务结束，避免重复启动多个连接器。

## 7. 发布

GitHub推送只更新源码，**不会自动更新现有Sites网站**。本项目当前没有配置GitHub Actions自动发布。

更新Sites时使用其官方源码工作流：保留站点ID和访问范围，验证并构建，推送准确源码状态，保存对应版本，再部署。凭据只经隐藏标准输入提供，不写入命令行、文件或README。

## 8. IDEA / GitHub连接失败

如果IDEA已成功创建GitHub仓库，但Git报`Failed to connect to github.com port 443`，失败发生在Git HTTPS连接阶段。IDEA自身代理设置不等于外部Git配置。

先确认本机代理实际监听地址。当前机器验证通过的是`127.0.0.1:7078`，在当前项目目录配置：

```powershell
git config --local http.https://github.com.proxy http://127.0.0.1:7078
git ls-remote origin
git push -u origin main
```

空仓库的`git ls-remote origin`可成功退出而没有输出。这不等于推送已完成。代理端口只对当前机器成立；代理关闭或迁移后可取消本仓库配置：

```powershell
git config --local --unset http.https://github.com.proxy
```

无需重建仓库，也不要通过关闭TLS证书验证处理连接超时。
