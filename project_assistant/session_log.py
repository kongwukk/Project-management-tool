from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .models import ChatMessage


class SessionLogger:
    def __init__(self, data_dir: Path) -> None:
        self.sessions_dir = data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save(self, messages: Sequence[ChatMessage], path: Optional[Path] = None) -> Path:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        target = path or self._new_session_path()
        target.write_text(self._render_markdown(messages), encoding="utf-8")
        return target

    def _new_session_path(self) -> Path:
        filename = datetime.now().strftime("%Y%m%d_%H%M%S.md")
        return self.sessions_dir / filename

    def _render_markdown(self, messages: Sequence[ChatMessage]) -> str:
        lines = [
            "# 对话记录",
            "",
            f"- 保存时间：{datetime.now().isoformat(timespec='seconds')}",
            "",
        ]
        for message in messages:
            speaker = {"user": "用户", "assistant": "助手", "system": "系统"}.get(message.role, message.role)
            lines.extend(
                [
                    f"## {speaker} - {message.timestamp}",
                    "",
                    message.content.strip(),
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

