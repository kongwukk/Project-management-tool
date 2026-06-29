from __future__ import annotations

import time
from typing import Dict, Iterable, List

from .models import ModelConfig


MessagePayload = List[Dict[str, str]]


class ModelClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def chat(self, model_config: ModelConfig, messages: MessagePayload, *, retries: int = 1) -> str:
        client = self._build_client(model_config)
        kwargs = self._request_kwargs(model_config, messages)

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1)
                    continue
                break
        raise ModelClientError(f"模型请求失败：{last_error}") from last_error

    def stream_chat(self, model_config: ModelConfig, messages: MessagePayload) -> Iterable[str]:
        client = self._build_client(model_config)
        kwargs = self._request_kwargs(model_config, messages)
        kwargs["stream"] = True
        try:
            stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield text
        except Exception as exc:
            raise ModelClientError(f"流式模型请求失败：{exc}") from exc

    def test_connection(self, model_config: ModelConfig) -> str:
        messages = [
            {"role": "system", "content": "你是一个连接测试助手，只用一句话回答。"},
            {"role": "user", "content": "请回复：连接成功"},
        ]
        return self.chat(model_config, messages, retries=0)

    def _build_client(self, model_config: ModelConfig):
        if not model_config.api_key.strip():
            raise ModelClientError("请先填写 API Key。")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelClientError("缺少 openai 依赖，请先运行：pip install openai") from exc

        base_url = model_config.base_url.strip() or None
        return OpenAI(
            api_key=model_config.api_key.strip(),
            base_url=base_url,
            timeout=model_config.timeout_seconds,
        )

    def _request_kwargs(self, model_config: ModelConfig, messages: MessagePayload) -> Dict[str, object]:
        kwargs: Dict[str, object] = {
            "model": model_config.model_name.strip(),
            "messages": messages,
            "temperature": model_config.temperature,
        }
        if model_config.max_tokens > 0:
            kwargs["max_tokens"] = model_config.max_tokens
        return kwargs

