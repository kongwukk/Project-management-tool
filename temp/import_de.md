# DeepSeek API 导入说明

本文档提炼自 `wechat-daily` 中的 DeepSeek 调用方式，方便把同样的能力迁移到其他 Python 项目。

## 1. 核心依赖

`wechat-daily` 使用 OpenAI Python SDK 的兼容接口调用 DeepSeek。

```bash
pip install openai pyyaml
```

如果你的项目不需要从 YAML 文件读取配置，只安装 `openai` 即可。

## 2. 配置方式

在 `wechat-daily/config.yaml.example` 中，DeepSeek 相关配置位于 `ai` 节：

```yaml
ai:
  provider: "deepseek"
  api_key: "YOUR_DEEPSEEK_API_KEY"
  model: "deepseek-chat"
  max_tokens: 4096
  # base_url: "https://api.deepseek.com"
```

字段说明：

- `provider`: 当前项目里用于区分不同 AI 后端，使用 DeepSeek 时填 `deepseek`。
- `api_key`: DeepSeek API Key，建议不要提交到 Git。
- `model`: 默认使用 `deepseek-chat`。
- `max_tokens`: 单次回复最大 token 数，当前项目默认 `4096`。
- `base_url`: DeepSeek 的 OpenAI 兼容接口地址。留空时，代码默认使用 `https://api.deepseek.com`。

当前项目中的默认映射：

```python
API_BASES = {
    "deepseek": "https://api.deepseek.com",
}

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
}
```

## 3. 最小可复用调用方法

下面这段代码就是把消息发送到 DeepSeek API 的最小实现，可以复制到其他项目中，例如保存为 `deepseek_client.py`。

```python
from openai import OpenAI


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def send_to_deepseek(
    api_key: str,
    message: str,
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEEPSEEK_BASE_URL,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """Send one user message to DeepSeek and return the assistant text."""
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": message},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content or ""
```

使用示例：

```python
from deepseek_client import send_to_deepseek


api_key = "YOUR_DEEPSEEK_API_KEY"
answer = send_to_deepseek(api_key, "请用三句话总结今天的项目进展。")
print(answer)
```

## 4. 支持 system prompt 的版本

如果你的项目需要更稳定的角色设定，可以使用 `system` + `user` 两段消息。

```python
from openai import OpenAI


def chat_with_deepseek(
    api_key: str,
    user_message: str,
    *,
    system_prompt: str = "你是一个严谨、简洁的中文助手。",
    model: str = "deepseek-chat",
    base_url: str = "https://api.deepseek.com",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content or ""
```

## 5. 从 YAML 配置读取并调用

如果想沿用 `wechat-daily` 的配置风格，可以这样读取配置：

```python
from pathlib import Path

import yaml
from openai import OpenAI


API_BASES = {
    "deepseek": "https://api.deepseek.com",
    "newapi": "http://127.0.0.1:3000/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai": "https://api.openai.com/v1",
}

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "newapi": "gpt-4o-mini",
    "qwen": "qwen-plus",
    "openai": "gpt-4o",
}


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def send_ai_message(config: dict, message: str) -> str:
    ai_cfg = config["ai"]
    provider = ai_cfg.get("provider", "deepseek").lower()
    api_key = ai_cfg["api_key"]
    base_url = ai_cfg.get("base_url") or API_BASES.get(provider, API_BASES["deepseek"])
    model = ai_cfg.get("model") or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["deepseek"])
    max_tokens = ai_cfg.get("max_tokens", 4096)

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": message}],
        max_tokens=max_tokens,
        temperature=0.3,
    )

    return response.choices[0].message.content or ""
```

调用：

```python
config = load_config("config.yaml")
answer = send_ai_message(config, "把下面的聊天记录总结成 Markdown。")
print(answer)
```

## 6. 在其他项目中导入该能力

推荐迁移步骤：

1. 在新项目中安装依赖：`pip install openai pyyaml`。
2. 新建 `config.yaml`，写入 `ai.provider`、`ai.api_key`、`ai.model`、`ai.max_tokens`。
3. 复制本文第 3 节的 `send_to_deepseek`，或第 5 节的配置版 `send_ai_message`。
4. 在业务代码中把需要分析的文本拼成 prompt，再调用发送函数。

示例业务调用：

```python
chat_text = """
[09:10] 张三: 今天接口联调完成了吗？
[09:12] 李四: 已经完成，还剩文档整理。
"""

prompt = f"""请总结下面的聊天记录，并提取待办事项：

{chat_text}
"""

summary = send_to_deepseek(api_key="YOUR_DEEPSEEK_API_KEY", message=prompt)
print(summary)
```

## 7. 与 `wechat-daily` 源码的对应关系

当前项目中有两处核心实现：

- `wechat-daily/ai_analyzer.py`
  - `AIAnalyzer.__init__`: 读取 `config["ai"]`，初始化 `OpenAI(api_key=api_key, base_url=base_url)`。
  - `AIAnalyzer._call_api`: 调用 `client.chat.completions.create(...)` 发送 prompt。
- `wechat-daily/summarize_export_chat.py`
  - `call_model`: 从配置读取 `provider`、`api_key`、`base_url`、`model`、`max_tokens`，再发送聊天总结 prompt。

本质调用链：

```text
读取配置 -> 创建 OpenAI 兼容客户端 -> 组装 messages -> chat.completions.create -> 读取 response.choices[0].message.content
```

## 8. 安全建议

- 不要把真实 API Key 写入公开仓库。
- 可以用环境变量保存密钥，例如 `DEEPSEEK_API_KEY`，再在代码中读取。
- 发送聊天记录前，确认内容是否包含隐私、密钥、身份证号、手机号等敏感信息。
- 接入生产系统时，建议加上异常处理、日志脱敏、超时控制和重试策略。
