from __future__ import annotations

import re
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

    def build_updated_markdown(
        self,
        *,
        user_input: str,
        assistant_reply: str,
        current_markdown: str,
        file_path: str,
        attachments: Sequence[ParsedDocument],
        model_config: ModelConfig,
    ) -> str:
        attachment_text = ""
        if attachments:
            attachment_text = "\n\n".join(document.prompt_block() for document in attachments)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是项目 Markdown 文件维护助手。"
                    "你的任务是根据用户需求、当前项目文件内容、附件内容和上一轮助手回复，"
                    "输出更新后的完整 Markdown 文件内容。"
                    "只输出 Markdown 正文，不要解释，不要代码围栏。"
                    "必须保留原文件中仍然有用的信息，只执行用户明确要求的变更。"
                    "如果用户要求记录进展、添加任务、勾选完成、修改状态或更新计划，请直接整合到文件中。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"目标文件：{file_path}\n\n"
                    f"当前 Markdown 内容：\n{current_markdown}\n\n"
                    f"用户需求：\n{user_input}\n\n"
                    f"上一轮助手回复：\n{assistant_reply}\n\n"
                    f"本轮附件内容：\n{attachment_text or '（无）'}\n\n"
                    "请输出更新后的完整 Markdown 文件内容。"
                ),
            },
        ]
        updated = self.model_client.chat(model_config, messages)
        return _strip_markdown_fence(updated)

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


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:markdown|md)?\s*(.*?)\s*```", stripped, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else stripped
