# 智能项目助手 (Project Assistant)

一个本地桌面项目管理对话工具。它会读取项目目录下的 Markdown 文件作为上下文，支持上传 Office 文档，并通过 OpenAI 兼容接口调用 DeepSeek、OpenAI、本地模型或其他大模型服务。

## 功能

- 项目上下文感知：扫描指定目录下的 `.md` 文件，提取标题、任务列表、表格片段和正文。
- 多模型配置：支持新增、编辑、删除、切换、测试 OpenAI 兼容模型 API。
- Office 文件解析：支持 `.docx`、`.pptx`、`.xlsx`，解析结果会随本轮对话注入。
- 桌面对话界面：模型下拉、API 配置弹窗、项目路径刷新、附件列表、时间戳消息记录。
- 本地持久化：配置保存到 `~/.project-assistant/config.json`，会话保存到 `~/.project-assistant/sessions/`。

## 安装

```bash
pip install -r requirements.txt
```

Tkinter 通常随 Python 一起安装。如果你的 Python 发行版未包含 Tkinter，需要额外安装对应系统包。

## 启动

```bash
python main.py
```

首次启动后：

1. 点击 `配置 API`，填写模型名称、API 地址、API Key 等参数。
2. 点击 `选择项目`，选择包含 Markdown 文件的项目目录；默认目录是仓库内的 `projects/`。
3. 可点击 `上传文件` 加载 Word、PowerPoint 或 Excel 文件。
4. 在底部输入框输入问题，按 Enter 发送，按 Shift+Enter 换行。

## 目录结构

```text
project_assistant/
  config_store.py      # 配置持久化与 API Key 本地加密保存
  context.py           # Markdown 项目上下文扫描与合并
  file_processor.py    # Office 文件解析
  model_client.py      # OpenAI 兼容模型调用与连接测试
  chat_engine.py       # Prompt 组装与对话引擎
  session_log.py       # Markdown 会话记录
  models.py            # 数据模型
  ui/app.py            # Tkinter 桌面界面
projects/              # 默认 Markdown 项目目录
main.py                # 应用入口
```

## DeepSeek 示例

```text
显示名称：DeepSeek
模型名称：deepseek-chat
API 地址：https://api.deepseek.com
API Key：你的 DeepSeek API Key
```

## 安全说明

API Key 会以轻量本地加密形式写入配置文件，避免明文保存。若要用于生产环境，建议进一步接入系统密钥链或企业级密钥管理方案。

