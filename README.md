# Project-management-tool
This is an internal tool designed to help everyone effectively manage ongoing projects. It uses the DeepSeek API for AI-related tasks, and all configurations can be completed directly through the GUI, without using the command line.


##  快速开始

### 1. 环境准备
确保你的电脑已安装 Python 3.8+。

### 2. 安装依赖
在项目根目录下运行以下命令：
```bash
pip install fastapi uvicorn openai pypandoc pandas openpyxl python-multipart
```

> **️ 重要提示**：`pypandoc` 解析 Word 和 PPT 需要系统安装 Pandoc 工具。
> - **Windows**: 运行 `choco install pandoc` 或前往官网下载 Windows 安装包
> - **Mac**: 运行 `brew install pandoc`
> - **Linux**: 运行 `sudo apt-get install pandoc`

### 3. 启动服务
```bash
python main.py
```
服务默认运行在 `http://localhost:8000`。

## ️ API 接口说明

### 1. 配置模型
- **URL**: `POST /api/configure-model`
- **Body**:
```json
{
  "api_key": "sk-xxxx",
  "model_name": "gpt-3.5-turbo",
  "base_url": "https://api.openai.com/v1" 
}
```
> 注：`base_url` 为可选参数，用于兼容各类第三方大模型代理接口。

### 2. 发送对话与上传文件
- **URL**: `POST /api/chat`
- **Content-Type**: `multipart/form-data`
- **参数**:
  - `message`: 用户输入的文本
  - `file`: (可选) 上传的 Word/PPT/Excel 文件

##  项目状态管理
服务启动时会在同级目录自动生成 `project_status.md`。大模型在回复时会读取该文件的内容作为上下文。你可以随时手动编辑该文件来更新项目的最新进展。
```

你可以直接全选复制上面的内容，保存为 `README.md` 即可。如果在本地运行环境或对接前端时遇到任何问题，随时告诉我！


