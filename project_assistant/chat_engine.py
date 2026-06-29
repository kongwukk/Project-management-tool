from __future__ import annotations

from typing import Dict, List, Sequence

from .context import ProjectContextManager
from .model_client import OpenAICompatibleClient
from .models import ChatMessage, ModelConfig, ParsedDocument


class ChatEngine:
    def __init__(
        self,
        context_manager: ProjectContextManager,
        model_client: OpenAICompatibleClient,
        *,
        history_window: int = 8,
    ) -> None:
        self.context_manager = context_manager
        self.model_client = model_client
        self.history_window = history_window

    def send(
        self,
        user_input: str,
        *,
        history: Sequence[ChatMessage],
        attachments: Sequence[ParsedDocument],
        model_config: ModelConfig,
    ) -> str:
        messages = self.build_messages(user_input, history=history, attachments=attachments)
        return self.model_client.chat(model_config, messages)

    def build_messages(
        self,
        user_input: str,
        *,
        history: Sequence[ChatMessage],
        attachments: Sequence[ParsedDocument],
    ) -> List[Dict[str, str]]:
        system_prompt = (
            "你是一个严谨、主动的智能项目协作助手。"
            "回答必须优先依据项目 Markdown 上下文；如果上下文不足，请明确说明缺口并给出可执行建议。\n\n"
            f"{self.context_manager.build_context()}"
        )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        visible_history = [message for message in history if message.role in {"user", "assistant"}]
        for message in visible_history[-self.history_window * 2 :]:
            messages.append({"role": message.role, "content": message.content})

        user_content = user_input.strip()
        if attachments:
            file_blocks = "\n\n".join(document.prompt_block() for document in attachments)
            user_content = f"{user_content}\n\n用户本轮附加文件内容：\n{file_blocks}".strip()
        messages.append({"role": "user", "content": user_content})
        return messages

