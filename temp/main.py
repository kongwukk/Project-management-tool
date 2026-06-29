# main.py
import os
import json
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import openai
import pypandoc
import pandas as pd

app = FastAPI()

# 允许跨域请求（方便本地前端调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局配置（实际项目中可存入数据库或本地配置文件）
MODEL_CONFIG = {
    "api_key": "",
    "model_name": "gpt-3.5-turbo",
    "base_url": ""
}

PROJECT_MD_PATH = "project_status.md"

# 初始化项目MD文件
def init_project_md():
    if not os.path.exists(PROJECT_MD_PATH):
        with open(PROJECT_MD_PATH, "w", encoding="utf-8") as f:
            f.write("# 项目当前状态\n\n- 项目刚启动，暂无具体进展。\n")

init_project_md()

# 读取项目MD文件内容
def get_project_context():
    try:
        with open(PROJECT_MD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取项目状态文件失败: {str(e)}"

# 解析上传的文件
async def parse_file(file: UploadFile):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    content = ""
    
    try:
        if ext == ".docx":
            # 使用pypandoc将word转为纯文本
            content = pypandoc.convert_file(file.file, 'plain', format='docx')
        elif ext == ".pptx":
            content = pypandoc.convert_file(file.file, 'plain', format='pptx')
        elif ext in [".xlsx", ".xls"]:
            # 使用pandas读取Excel
            df = pd.read_excel(file.file)
            content = df.to_string()
        else:
            raise ValueError("不支持的文件格式，请上传 Word, PPT 或 Excel 文件")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")
    
    return content

# 配置模型接口
class ModelConfigRequest(BaseModel):
    api_key: str
    model_name: str
    base_url: Optional[str] = None

@app.post("/api/configure-model")
async def configure_model(config: ModelConfigRequest):
    MODEL_CONFIG["api_key"] = config.api_key
    MODEL_CONFIG["model_name"] = config.model_name
    MODEL_CONFIG["base_url"] = config.base_url
    return {"message": "模型配置成功", "config": MODEL_CONFIG}

# 对话与文件上传接口
@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    if not MODEL_CONFIG["api_key"]:
        raise HTTPException(status_code=400, detail="请先配置大模型 API Key")

    # 1. 获取当前项目状态作为上下文
    project_context = get_project_context()
    
    # 2. 处理上传的文件
    file_content = ""
    if file:
        file_content = await parse_file(file)
        file_content = f"\n[用户上传的文件内容摘要]:\n{file_content[:2000]}" # 截取前2000字符防止超token

    # 3. 组装 Prompt
    system_prompt = (
        f"你是一个智能项目协作助手。请根据以下当前项目的状态来回答用户的问题。\n"
        f"【当前项目状态】:\n{project_context}\n"
        f"{file_content}"
    )
    
    # 4. 调用大模型
    try:
        client = openai.OpenAI(api_key=MODEL_CONFIG["api_key"], base_url=MODEL_CONFIG.get("base_url"))
        response = client.chat.completions.create(
            model=MODEL_CONFIG["model_name"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        ai_reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"大模型请求失败: {str(e)}")

    return {"reply": ai_reply}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)