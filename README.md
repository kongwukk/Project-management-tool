# 智能项目助手 (Project Assistant)

一个本地桌面项目管理对话工具。它会读取项目目录下的 Markdown 文件作为上下文，支持上传 Office 文档，并通过 OpenAI 兼容接口调用 DeepSeek、OpenAI、本地模型或其他大模型服务。

## 运行平台

本项目是 Python + Tkinter 桌面应用，不依赖 Linux 专属能力，支持 Windows 10/11、Linux 和 macOS。当前仓库已提供 Windows 10 推荐启动脚本。

## 功能

- 项目上下文感知：扫描指定目录下的 `.md` 文件，提取标题、任务列表、表格片段和正文。
- 多模型配置：支持新增、编辑、删除、切换、测试 OpenAI 兼容模型 API。
- Office 文件解析：支持 `.docx`、`.pptx`、`.xlsx`，解析结果会随本轮对话注入。
- 桌面对话界面：模型下拉、API 配置弹窗、项目路径刷新、附件列表、时间戳消息记录。
- 对话复制与日志：支持复制聊天内容，或按当前时间导出 `.log` 对话日志。
- 自动更新项目文件：当用户明确要求更新项目状态、任务、进度或 Markdown 文件时，模型会生成新的项目 `.md` 内容并写回当前选择的文件。
- 本地持久化：配置保存到 `~/.project-assistant/config.json`，会话保存到 `~/.project-assistant/sessions/`。

## Windows 10 使用方式

### 环境要求

- Windows 10 64 位。
- Python 3.10 或更高版本。
- 安装 Python 时建议勾选 `Add python.exe to PATH`。
- 首次安装依赖和调用在线模型时需要网络连接。

### 推荐启动

在项目根目录双击运行：

```bat
scripts\run_windows.bat
```

该脚本会自动：

1. 切换到项目根目录。
2. 创建 `.venv` 虚拟环境。
3. 安装 `requirements.txt` 中的依赖。
4. 启动桌面程序。

### 手动启动

如果你更习惯命令行，也可以在 PowerShell 或 CMD 中执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

如果系统没有 `py` 启动器，可以把第一行改为：

```powershell
python -m venv .venv
```

## Linux/macOS 使用方式

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Tkinter 通常随 Python 一起安装。如果你的 Python 发行版未包含 Tkinter，需要额外安装对应系统包。

首次启动后：

1. 点击 `配置 API`，填写模型名称、API 地址、API Key 等参数。
2. 点击 `选择项目文件`，选择一个 `.md` Markdown 文件作为当前项目上下文。
3. 可点击 `上传文件` 加载 Word、PowerPoint 或 Excel 文件。
4. 在底部输入框输入问题，按 Enter 发送，按 Shift+Enter 换行。
5. 点击 `复制对话` 可复制当前会话；点击 `保存日志` 会在 `~/.project-assistant/sessions/` 下生成按当前时间命名的 `.log` 文件。

默认配置仍会读取仓库内的 `projects/` 示例目录；一旦点击 `选择项目文件`，后续切换就会以选中的单个 `.md` 文件为上下文。

## 更新项目 Markdown 文件

选择项目 `.md` 文件后，普通提问只会输出到对话窗口；当输入中包含明确的写入意图时，程序会在模型回答后自动更新当前 `.md` 文件。

示例：

```text
请把今天接口联调完成、还剩文档整理这件事更新到项目文件里。
```

```text
请新增一个待办：明天检查 Windows 10 打包流程，并写入项目计划。
```

为避免普通问答误改文件，只有类似“更新项目文件 / 写入 md / 添加任务 / 修改进度 / 记录状态”等明确表达才会触发写回。

## 目录结构

```text
project_assistant/
  config_store.py      # 配置持久化与 API Key 本地加密保存
  context.py           # Markdown 项目上下文扫描与合并
  file_processor.py    # Office 文件解析
  model_client.py      # OpenAI 兼容模型调用与连接测试
  chat_engine.py       # Prompt 组装与对话引擎
  session_log.py       # Markdown 会话记录与 .log 导出
  models.py            # 数据模型
  ui/app.py            # Tkinter 桌面界面
projects/              # 默认 Markdown 项目目录
scripts/run_windows.bat # Windows 10 一键启动脚本
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
