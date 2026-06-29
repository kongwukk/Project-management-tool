# 模块对应关系

本文档说明 `PROJECT_DESCRIPTION.md` 中的功能模块在代码中的落点。

## 2.1 主界面

- 文件：`project_assistant/ui/app.py`
- 内容：模型下拉选择、API 配置弹窗、项目路径选择与刷新、滚动对话区、多行输入框、附件上传与移除、消息时间戳、Enter/Shift+Enter 交互。

## 2.2 模型管理

- 文件：`project_assistant/ui/app.py`
- 文件：`project_assistant/config_store.py`
- 文件：`project_assistant/model_client.py`
- 内容：模型新增、编辑、删除、切换、测试连接；配置写入 `~/.project-assistant/config.json`。

## 2.3 文件处理

- 文件：`project_assistant/file_processor.py`
- 内容：解析 `.docx` 段落与表格、`.pptx` 幻灯片文本与备注、`.xlsx` 工作表内容，并输出结构化文本。

## 2.4 项目上下文管理

- 文件：`project_assistant/context.py`
- 内容：扫描项目目录下所有 Markdown 文件，提取标题、任务列表、表格片段，并合并为系统提示上下文。界面支持手动刷新，每次发送前也会刷新。

## 2.5 对话引擎

- 文件：`project_assistant/chat_engine.py`
- 文件：`project_assistant/model_client.py`
- 内容：组装系统提示、历史对话、当前用户输入和附件内容，通过 OpenAI 兼容客户端请求模型。

## 2.6 配置持久化

- 文件：`project_assistant/config_store.py`
- 内容：保存模型列表、当前模型、项目目录、主题和历史窗口设置。

## 2.7 日志与记录

- 文件：`project_assistant/session_log.py`
- 内容：将每次会话保存为 Markdown 文件，路径为 `~/.project-assistant/sessions/`。

