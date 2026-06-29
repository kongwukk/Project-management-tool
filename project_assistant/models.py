from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ModelConfig:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "DeepSeek"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    provider: str = "openai-compatible"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_seconds: int = 60

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        return cls(
            id=data.get("id") or uuid4().hex,
            name=data.get("name") or "未命名模型",
            model_name=data.get("model_name") or data.get("model") or "deepseek-chat",
            base_url=data.get("base_url") or "",
            api_key=data.get("api_key") or "",
            provider=data.get("provider") or "openai-compatible",
            temperature=float(data.get("temperature", 0.3)),
            max_tokens=int(data.get("max_tokens", 4096)),
            timeout_seconds=int(data.get("timeout_seconds", 60)),
        )

    def to_dict(self, *, include_api_key: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
        }
        if include_api_key:
            data["api_key"] = self.api_key
        return data


@dataclass
class AppConfig:
    project_dir: str
    selected_model_id: Optional[str] = None
    theme: str = "light"
    history_window: int = 8
    models: List[ModelConfig] = field(default_factory=list)

    def selected_model(self) -> Optional[ModelConfig]:
        if self.selected_model_id:
            for model in self.models:
                if model.id == self.selected_model_id:
                    return model
        return self.models[0] if self.models else None


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class ParsedDocument:
    filename: str
    source_type: str
    content: str
    path: str = ""

    def prompt_block(self, max_chars: int = 12000) -> str:
        text = self.content.strip()
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "\n...[内容已截断]"
        return f"### {self.filename} ({self.source_type})\n{text}"

