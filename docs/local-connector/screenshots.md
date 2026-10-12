# 截图识题

在真题解析模式上传或粘贴PNG/JPEG/WebP图片，一道题最多2张。浏览器转为PNG，最长边2200像素、每张转换后最多2MB；服务器按实际字节、PNG头、尺寸和SHA-256验证。不收外部图片URL，也不接受客户端自定义存储路径。

所有者同源POST `/api/textbook/screenshots` 使用multipart字段requestId和images，私有R2保存原题。内部recognize任务与现有问答/点评共用互斥队列，普通会话列表和多轮历史不含转录任务。识别结果最多2000字，注意事项最多1000字，结果不提前作答；无法识别的位置提示核对，不按常识补造。

识别完成后文字填入输入框，用户修改后点击“我已核对文字，保留原图解析”再发送。POST chat带screenshotId，仅接受本人完成的识别任务；原图关联由服务器获取。失败的图文题重试继续用同一原图。回答里的“查看原题截图”可展开回看，图片GET按owner检查，返回private/no-store。

本地桥接在有效运行lease下执行screenshotRead，从云获取图像，传入questionImages。识别调用现有MiniMax原页模型；原题解析以修正后的文字检索教材，原题截图也提供给图文模型。原题最多2张，教材来源原页继续最多2张；questionImages不是教材source，不生成教材引用。图文生成失败时直接提示重试，不自动丢弃原题截图以纯文字作答。

0008迁移只增加screenshot_json/recognition_json/screenshot_ready，旧任务保留原逻辑。连接器升级后声明screenshotReady才启用截图提交；前端图像处理可在连接恢复前完成。新截图任务保留私有图像用于解析、重试与回看，不将用户原题写入教材向量库。

验证记录位于本机F:/daily/output/sysarch-screenshot。真实合成题包含文字选项和需求→设计实现示意图，已验证MiniMax转录和同轮原图解析。接口采用实际路由SQLite/R2适配测试；浏览器交互验证沿用此前限制，未宣称已验证拖拽或摄像头输入。
