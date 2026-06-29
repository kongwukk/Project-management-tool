from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


TASK_PATTERN = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+.+$")
HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")


@dataclass
class MarkdownDocument:
    path: Path
    relative_path: str
    content: str
    headings: List[str]
    tasks: List[str]
    tables: List[str]

    @property
    def title(self) -> str:
        return self.headings[0] if self.headings else self.path.stem


class ProjectContextManager:
    def __init__(self, project_dir: str | Path, prefix: str = "当前项目状态如下：") -> None:
        self.project_dir = Path(project_dir)
        self.prefix = prefix
        self.documents: List[MarkdownDocument] = []
        self.last_refreshed_at: str = ""

    def set_project_dir(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self.documents = []
        self.last_refreshed_at = ""

    def refresh(self) -> List[MarkdownDocument]:
        self.project_dir.mkdir(parents=True, exist_ok=True)
        documents = [self._read_markdown(path) for path in self._iter_markdown_files()]
        self.documents = documents
        self.last_refreshed_at = datetime.now().isoformat(timespec="seconds")
        return documents

    def build_context(self, max_chars: int = 60000) -> str:
        if not self.last_refreshed_at:
            self.refresh()

        if not self.documents:
            return f"{self.prefix}\n\n项目目录 `{self.project_dir}` 下暂未发现 Markdown 文件。"

        parts: List[str] = [
            self.prefix,
            f"项目目录：{self.project_dir}",
            f"刷新时间：{self.last_refreshed_at}",
            f"Markdown 文件数：{len(self.documents)}",
            "",
        ]
        for document in self.documents:
            parts.append(self._document_block(document))

        context = "\n".join(parts).strip()
        if len(context) > max_chars:
            context = context[:max_chars].rstrip() + "\n\n...[项目上下文已截断]"
        return context

    def summary(self) -> str:
        if not self.last_refreshed_at:
            self.refresh()
        return f"{len(self.documents)} 个 Markdown 文件，刷新时间 {self.last_refreshed_at or '未刷新'}"

    def _iter_markdown_files(self) -> Iterable[Path]:
        excluded = {".git", ".venv", "__pycache__", "node_modules", ".project-assistant"}
        files = []
        for path in self.project_dir.rglob("*.md"):
            if any(part in excluded for part in path.parts):
                continue
            files.append(path)
        return sorted(files, key=lambda item: str(item).lower())

    def _read_markdown(self, path: Path) -> MarkdownDocument:
        content = path.read_text(encoding="utf-8", errors="replace")
        headings = [match.group(2).strip() for line in content.splitlines() if (match := HEADING_PATTERN.match(line))]
        tasks = [line.strip() for line in content.splitlines() if TASK_PATTERN.match(line)]
        tables = _extract_tables(content)
        try:
            relative_path = str(path.relative_to(self.project_dir))
        except ValueError:
            relative_path = str(path)
        return MarkdownDocument(
            path=path,
            relative_path=relative_path,
            content=content,
            headings=headings,
            tasks=tasks,
            tables=tables,
        )

    def _document_block(self, document: MarkdownDocument) -> str:
        parts = [
            f"## 文件：{document.relative_path}",
            f"标题：{document.title}",
        ]
        if document.headings:
            parts.append("### 标题结构")
            parts.extend(f"- {heading}" for heading in document.headings[:30])
        if document.tasks:
            parts.append("### 任务列表")
            parts.extend(document.tasks[:80])
        if document.tables:
            parts.append("### 表格片段")
            parts.extend(document.tables[:3])
        parts.append("### 正文")
        parts.append(document.content.strip() or "（空文件）")
        parts.append("")
        return "\n".join(parts)


def _extract_tables(content: str) -> List[str]:
    tables: List[str] = []
    current: List[str] = []
    for line in content.splitlines():
        if "|" in line and line.strip().startswith("|"):
            current.append(line.rstrip())
            continue
        if len(current) >= 2:
            tables.append("\n".join(current))
        current = []
    if len(current) >= 2:
        tables.append("\n".join(current))
    return tables

