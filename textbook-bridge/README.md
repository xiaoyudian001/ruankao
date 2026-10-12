# 本机教材问答连接器

源码对应已实现的普通问答、完整检索、多轮追问、教材图文、真题解析、截图识题与回忆点评。网站数据契约在相邻的`lib/textbook`和`app/api/textbook`目录，完整功能说明见[主README](../README.md)。

连接器主动请求固定网站的HTTPS接口领取任务，调用本机Langflow/Ollama后回传结果。`bridge.py`是主入口，`single_pass.py`负责证据准备和一次答案生成；`screenshots.py`、`exam.py`、`critique.py`处理相应输出契约。配置、知识库、模型权重和运行结果不在仓库中。

`start.ps1`在Windows读取DPAPI加密的本机配置，通过隐藏标准输入启动Python；`stop.ps1`等待当前任务处理完再停止。脚本中本机可执行文件路径及固定站点地址对应现有部署，迁移时需要核对，不能直接假设它们在新机器存在。

本机配置文件包括`config.json`、`page-source.json`、`single-pass-flows.json`及相关独立流程清单，均被Git忽略。真实连接密钥和MiniMax配置不得写入源码。原教材页读取会检查PDF哈希、页数和来源映射。

准备Python依赖后，在本目录运行：

```powershell
python -m unittest discover -p 'test*.py'
```

现有Windows部署曾完成61项检查；公开源码不带教材目录，缺少该目录时5项教材图示集成检查明确跳过，其余56项规则与模拟检查可执行。传输检查用临时模拟配置。真实`verify_*.py`脚本需要具体的Langflow流程与教材索引，部分会调用MiniMax，部分会读写当前部署的验证状态；运行前先查看脚本路径和目标，不把它们当成无网络的单元测试。

更多说明：[运行与部署](../docs/setup.zh-CN.md)、[截图识题](../docs/local-connector/screenshots.md)、[一次答案生成](../docs/local-connector/single-answer.md)。
