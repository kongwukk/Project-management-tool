from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional
from uuid import uuid4

from ..chat_engine import ChatEngine
from ..config_store import ConfigStore
from ..context import ProjectContextManager
from ..file_processor import FileProcessingError, SUPPORTED_EXTENSIONS, parse_office_file
from ..model_client import OpenAICompatibleClient
from ..models import AppConfig, ChatMessage, ModelConfig, ParsedDocument
from ..session_log import SessionLogger


class ProjectAssistantApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("智能项目助手")
        self.geometry("1080x760")
        self.minsize(860, 620)

        self.store = ConfigStore()
        self.app_config = self.store.load()
        self.context_manager = ProjectContextManager(self.app_config.project_dir)
        self.model_client = OpenAICompatibleClient()
        self.engine = ChatEngine(
            self.context_manager,
            self.model_client,
            history_window=self.app_config.history_window,
        )
        self.logger = SessionLogger(self.store.data_dir)

        self.messages: List[ChatMessage] = []
        self.attachments: List[ParsedDocument] = []
        self.current_session_path: Optional[Path] = None
        self.model_name_to_id: Dict[str, str] = {}

        self._build_style()
        self._build_ui()
        self._refresh_model_combo()
        self.refresh_project_context(show_message=False)

    def _build_style(self) -> None:
        self.configure(background="#f6f7f9")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background="#f6f7f9")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Muted.TLabel", background="#f6f7f9", foreground="#5f6673")
        style.configure("Status.TLabel", background="#f6f7f9", foreground="#5f6673")
        style.configure("Primary.TButton", padding=(14, 7))
        style.configure("TButton", padding=(10, 6))
        style.configure("TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("TEntry", padding=(6, 4))

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, style="Root.TFrame", padding=(12, 10, 12, 8))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(5, weight=1)

        ttk.Label(top, text="模型", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(top, textvariable=self.model_var, state="readonly", width=26)
        self.model_combo.grid(row=0, column=1, padx=(8, 8), sticky="w")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        ttk.Button(top, text="配置 API", command=self._open_model_dialog).grid(row=0, column=2, padx=(0, 12))
        ttk.Button(top, text="选择项目", command=self._choose_project_dir).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(top, text="刷新", command=lambda: self.refresh_project_context(show_message=True)).grid(
            row=0,
            column=4,
            padx=(0, 12),
        )

        self.project_path_var = tk.StringVar()
        ttk.Label(top, textvariable=self.project_path_var, style="Muted.TLabel").grid(row=0, column=5, sticky="ew")

        center = ttk.Frame(self, style="Panel.TFrame", padding=(12, 12, 12, 12))
        center.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        self.chat_text = tk.Text(
            center,
            wrap="word",
            state="disabled",
            padx=16,
            pady=14,
            relief="flat",
            background="#ffffff",
            foreground="#1f2933",
            insertbackground="#1f2933",
            font=("Microsoft YaHei UI", 10),
        )
        scrollbar = ttk.Scrollbar(center, orient="vertical", command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        self.chat_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._configure_chat_tags()

        bottom = ttk.Frame(self, style="Root.TFrame", padding=(12, 0, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.attachments_frame = ttk.Frame(bottom, style="Root.TFrame")
        self.attachments_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.attachments_frame.columnconfigure(0, weight=1)

        input_row = ttk.Frame(bottom, style="Root.TFrame")
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_row,
            height=4,
            wrap="word",
            padx=10,
            pady=8,
            relief="solid",
            borderwidth=1,
            background="#ffffff",
            foreground="#1f2933",
            insertbackground="#1f2933",
            font=("Microsoft YaHei UI", 10),
        )
        self.input_text.grid(row=0, column=0, sticky="ew")
        self.input_text.bind("<Shift-Return>", self._insert_newline)
        self.input_text.bind("<Return>", self._handle_enter)

        actions = ttk.Frame(input_row, style="Root.TFrame")
        actions.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.upload_button = ttk.Button(actions, text="上传文件", command=self.upload_files)
        self.upload_button.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.send_button = ttk.Button(actions, text="发送", style="Primary.TButton", command=self.send_message)
        self.send_button.grid(row=1, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bottom, textvariable=self.status_var, style="Status.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))

        self._render_attachments()
        self._append_system_message("已启动。请选择项目目录、配置 API，然后开始对话。")

    def _configure_chat_tags(self) -> None:
        self.chat_text.tag_configure("user_header", foreground="#255f9f", font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_configure(
            "user_body",
            background="#e8f1ff",
            lmargin1=92,
            lmargin2=92,
            rmargin=18,
            spacing1=4,
            spacing3=12,
        )
        self.chat_text.tag_configure("assistant_header", foreground="#256c4f", font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_configure(
            "assistant_body",
            background="#f1f5f3",
            lmargin1=18,
            lmargin2=18,
            rmargin=92,
            spacing1=4,
            spacing3=12,
        )
        self.chat_text.tag_configure("system_header", foreground="#6b7280", font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_configure(
            "system_body",
            foreground="#596273",
            background="#f5f6f8",
            lmargin1=36,
            lmargin2=36,
            rmargin=36,
            spacing1=4,
            spacing3=12,
        )

    def _refresh_model_combo(self) -> None:
        self.model_name_to_id.clear()
        values: List[str] = []
        for model in self.app_config.models:
            display = f"{model.name}  ·  {model.model_name}"
            suffix = 2
            unique_display = display
            while unique_display in self.model_name_to_id:
                unique_display = f"{display} ({suffix})"
                suffix += 1
            self.model_name_to_id[unique_display] = model.id
            values.append(unique_display)

        self.model_combo["values"] = values
        selected = self.app_config.selected_model()
        if selected:
            for display, model_id in self.model_name_to_id.items():
                if model_id == selected.id:
                    self.model_var.set(display)
                    break
        elif values:
            self.model_var.set(values[0])

    def _on_model_selected(self, _event: object = None) -> None:
        model_id = self.model_name_to_id.get(self.model_var.get())
        if model_id:
            self.store.set_selected_model(self.app_config, model_id)
            self.status_var.set("已切换模型")

    def _open_model_dialog(self) -> None:
        dialog = ModelConfigDialog(self, self.store, self.app_config, self.model_client)
        self.wait_window(dialog)
        self.app_config = self.store.load()
        self.engine.history_window = self.app_config.history_window
        self._refresh_model_combo()

    def _choose_project_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="选择项目 Markdown 目录",
            initialdir=self.app_config.project_dir,
            mustexist=False,
        )
        if not selected:
            return
        self.store.set_project_dir(self.app_config, selected)
        self.context_manager.set_project_dir(selected)
        self.refresh_project_context(show_message=True)

    def refresh_project_context(self, *, show_message: bool) -> None:
        try:
            documents = self.context_manager.refresh()
        except Exception as exc:
            messagebox.showerror("刷新失败", str(exc))
            self.status_var.set("项目上下文刷新失败")
            return

        self.project_path_var.set(f"{self.context_manager.project_dir}  ·  {len(documents)} 个 Markdown 文件")
        self.status_var.set(f"项目上下文已刷新：{len(documents)} 个 Markdown 文件")
        if show_message:
            self._append_system_message(f"项目上下文已刷新：{self.context_manager.summary()}")

    def upload_files(self) -> None:
        pattern = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="上传 Office 文件",
            filetypes=[
                ("Office 文件", pattern),
                ("Word", "*.docx"),
                ("PowerPoint", "*.pptx"),
                ("Excel", "*.xlsx"),
                ("所有文件", "*.*"),
            ],
        )
        if not paths:
            return

        errors: List[str] = []
        for path in paths:
            try:
                self.attachments.append(parse_office_file(path))
            except FileProcessingError as exc:
                errors.append(f"{Path(path).name}: {exc}")
            except Exception as exc:
                errors.append(f"{Path(path).name}: 文件解析失败：{exc}")

        self._render_attachments()
        if self.attachments:
            self.status_var.set(f"已加载 {len(self.attachments)} 个附件")
        if errors:
            messagebox.showwarning("部分文件未加载", "\n".join(errors))

    def _render_attachments(self) -> None:
        for child in self.attachments_frame.winfo_children():
            child.destroy()

        if not self.attachments:
            self.attachments_frame.grid_remove()
            return

        self.attachments_frame.grid()
        ttk.Label(self.attachments_frame, text="已加载文件", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        for index, document in enumerate(self.attachments, start=1):
            row = ttk.Frame(self.attachments_frame, style="Root.TFrame")
            row.grid(row=index, column=0, sticky="ew", pady=(4, 0))
            row.columnconfigure(0, weight=1)
            ttk.Label(row, text=f"{document.filename} · {document.source_type}", style="Muted.TLabel").grid(
                row=0,
                column=0,
                sticky="w",
            )
            ttk.Button(row, text="移除", command=lambda item=index - 1: self._remove_attachment(item)).grid(
                row=0,
                column=1,
                padx=(8, 0),
            )

    def _remove_attachment(self, index: int) -> None:
        if 0 <= index < len(self.attachments):
            del self.attachments[index]
        self._render_attachments()

    def _insert_newline(self, _event: tk.Event) -> str:
        self.input_text.insert("insert", "\n")
        return "break"

    def _handle_enter(self, event: tk.Event) -> Optional[str]:
        if event.state & 0x0001:
            return None
        self.send_message()
        return "break"

    def send_message(self) -> None:
        raw_text = self.input_text.get("1.0", "end-1c")
        user_text = raw_text.strip()
        if not user_text and not self.attachments:
            return

        model = self.app_config.selected_model()
        if model is None:
            messagebox.showinfo("需要配置模型", "请先新增并选择一个模型配置。")
            self._open_model_dialog()
            return
        if not model.api_key.strip():
            messagebox.showinfo("需要 API Key", "请先在模型配置中填写 API Key。")
            self._open_model_dialog()
            return

        history = list(self.messages)
        attachments = list(self.attachments)
        display_text = user_text or "请根据本轮附加文件进行分析。"
        if attachments:
            file_list = "\n".join(f"- {document.filename} ({document.source_type})" for document in attachments)
            display_text = f"{display_text}\n\n[本轮附加文件]\n{file_list}"

        self.input_text.delete("1.0", "end")
        self.attachments.clear()
        self._render_attachments()

        user_message = ChatMessage(role="user", content=display_text)
        self.messages.append(user_message)
        self._append_chat_message(user_message)
        self._set_busy(True)
        self.status_var.set("正在请求模型...")

        prompt_text = user_text or "请分析本轮附加文件，并给出结构化结论。"

        def worker() -> None:
            try:
                self.context_manager.refresh()
                reply = self.engine.send(
                    prompt_text,
                    history=history,
                    attachments=attachments,
                    model_config=model,
                )
                self.after(0, lambda: self._finish_reply(reply))
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish_error(error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_reply(self, reply: str) -> None:
        assistant_message = ChatMessage(role="assistant", content=reply.strip() or "（模型未返回内容）")
        self.messages.append(assistant_message)
        self._append_chat_message(assistant_message)
        self._save_session()
        self._set_busy(False)
        self.status_var.set("回复完成")

    def _finish_error(self, error: Exception) -> None:
        system_message = ChatMessage(role="system", content=f"请求失败：{error}")
        self.messages.append(system_message)
        self._append_chat_message(system_message)
        self._save_session()
        self._set_busy(False)
        self.status_var.set("请求失败")
        messagebox.showerror("请求失败", str(error))

    def _save_session(self) -> None:
        try:
            self.current_session_path = self.logger.save(self.messages, self.current_session_path)
        except Exception as exc:
            self.status_var.set(f"会话保存失败：{exc}")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        self.upload_button.configure(state=state)

    def _append_system_message(self, content: str) -> None:
        message = ChatMessage(role="system", content=content)
        self.messages.append(message)
        self._append_chat_message(message)

    def _append_chat_message(self, message: ChatMessage) -> None:
        speaker = {"user": "用户", "assistant": "助手", "system": "系统"}.get(message.role, message.role)
        header_tag = f"{message.role}_header" if message.role in {"user", "assistant", "system"} else "system_header"
        body_tag = f"{message.role}_body" if message.role in {"user", "assistant", "system"} else "system_body"
        timestamp = message.timestamp.replace("T", " ")

        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", f"{speaker} · {timestamp}\n", header_tag)
        self.chat_text.insert("end", f"{message.content.strip()}\n\n", body_tag)
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")


class ModelConfigDialog(tk.Toplevel):
    def __init__(
        self,
        parent: ProjectAssistantApp,
        store: ConfigStore,
        app_config: AppConfig,
        model_client: OpenAICompatibleClient,
    ) -> None:
        super().__init__(parent)
        self.title("模型 API 配置")
        self.geometry("760x460")
        self.minsize(720, 420)
        self.transient(parent)
        self.grab_set()

        self.store = store
        self.app_config = app_config
        self.model_client = model_client
        self.model_ids: List[str] = []
        self.current_model_id: Optional[str] = None

        self._build_ui()
        self._reload_list(select_id=self.app_config.selected_model_id)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=(12, 12, 8, 12))
        left.grid(row=0, column=0, sticky="ns")
        left.rowconfigure(0, weight=1)

        self.model_list = tk.Listbox(left, width=24, height=16, exportselection=False)
        self.model_list.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.model_list.bind("<<ListboxSelect>>", self._on_select)

        ttk.Button(left, text="新增", command=self._new_model).grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 4))
        ttk.Button(left, text="删除", command=self._delete_model).grid(row=1, column=1, sticky="ew", pady=(8, 0), padx=(4, 0))

        form = ttk.Frame(self, padding=(8, 12, 12, 12))
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)

        self.name_var = tk.StringVar()
        self.model_name_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.max_tokens_var = tk.StringVar(value="4096")
        self.temperature_var = tk.StringVar(value="0.3")
        self.timeout_var = tk.StringVar(value="60")

        self._field(form, "显示名称", self.name_var, 0)
        self._field(form, "模型名称", self.model_name_var, 1)
        self._field(form, "API 地址", self.base_url_var, 2)
        self._field(form, "API Key", self.api_key_var, 3, show="*")
        self._field(form, "最大 Token", self.max_tokens_var, 4)
        self._field(form, "温度", self.temperature_var, 5)
        self._field(form, "超时秒数", self.timeout_var, 6)

        hint = (
            "API 地址使用 OpenAI 兼容格式，例如 DeepSeek: https://api.deepseek.com，"
            "本地模型可填写 http://127.0.0.1:11434/v1。"
        )
        ttk.Label(form, text=hint, wraplength=470, foreground="#5f6673").grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

        actions = ttk.Frame(form)
        actions.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        actions.columnconfigure(3, weight=1)
        ttk.Button(actions, text="保存", command=self._save_model).grid(row=0, column=0, padx=(0, 8))
        self.test_button = ttk.Button(actions, text="测试连接", command=self._test_model)
        self.test_button.grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="关闭", command=self.destroy).grid(row=0, column=2, padx=(0, 8))

        self.status_var = tk.StringVar(value="")
        ttk.Label(form, textvariable=self.status_var, foreground="#5f6673").grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(12, 0),
        )

    def _field(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, *, show: str = "") -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(0, 8), padx=(0, 8))
        entry = ttk.Entry(parent, textvariable=variable, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=(0, 8))

    def _reload_list(self, *, select_id: Optional[str] = None) -> None:
        self.model_list.delete(0, "end")
        self.model_ids = []
        for model in self.app_config.models:
            self.model_ids.append(model.id)
            self.model_list.insert("end", model.name)

        if self.model_ids:
            index = self.model_ids.index(select_id) if select_id in self.model_ids else 0
            self.model_list.selection_clear(0, "end")
            self.model_list.selection_set(index)
            self.model_list.activate(index)
            self._load_model(self.app_config.models[index])
        else:
            self._new_model()

    def _on_select(self, _event: object = None) -> None:
        selection = self.model_list.curselection()
        if not selection:
            return
        index = selection[0]
        model_id = self.model_ids[index]
        for model in self.app_config.models:
            if model.id == model_id:
                self._load_model(model)
                return

    def _load_model(self, model: ModelConfig) -> None:
        self.current_model_id = model.id
        self.name_var.set(model.name)
        self.model_name_var.set(model.model_name)
        self.base_url_var.set(model.base_url)
        self.api_key_var.set(model.api_key)
        self.max_tokens_var.set(str(model.max_tokens))
        self.temperature_var.set(str(model.temperature))
        self.timeout_var.set(str(model.timeout_seconds))
        self.status_var.set("")

    def _new_model(self) -> None:
        self.current_model_id = None
        self.model_list.selection_clear(0, "end")
        self.name_var.set("新模型")
        self.model_name_var.set("deepseek-chat")
        self.base_url_var.set("https://api.deepseek.com")
        self.api_key_var.set("")
        self.max_tokens_var.set("4096")
        self.temperature_var.set("0.3")
        self.timeout_var.set("60")
        self.status_var.set("正在创建新模型配置")

    def _read_form(self) -> ModelConfig:
        name = self.name_var.get().strip()
        model_name = self.model_name_var.get().strip()
        if not name:
            raise ValueError("请填写显示名称。")
        if not model_name:
            raise ValueError("请填写模型名称。")

        try:
            max_tokens = int(self.max_tokens_var.get().strip())
            timeout_seconds = int(self.timeout_var.get().strip())
            temperature = float(self.temperature_var.get().strip())
        except ValueError as exc:
            raise ValueError("最大 Token、温度和超时秒数必须是数字。") from exc

        return ModelConfig(
            id=self.current_model_id or "",
            name=name,
            model_name=model_name,
            base_url=self.base_url_var.get().strip(),
            api_key=self.api_key_var.get().strip(),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )

    def _save_model(self) -> None:
        try:
            model = self._read_form()
        except ValueError as exc:
            messagebox.showwarning("无法保存", str(exc), parent=self)
            return

        if not model.id:
            model.id = uuid4().hex
        self.store.upsert_model(self.app_config, model)
        self.current_model_id = model.id
        self._reload_list(select_id=model.id)
        self.status_var.set("模型配置已保存")

    def _delete_model(self) -> None:
        if not self.current_model_id:
            return
        if not messagebox.askyesno("确认删除", "确定删除当前模型配置吗？", parent=self):
            return
        delete_id = self.current_model_id
        self.store.delete_model(self.app_config, delete_id)
        self.current_model_id = None
        self._reload_list(select_id=self.app_config.selected_model_id)
        self.status_var.set("模型配置已删除")

    def _test_model(self) -> None:
        try:
            model = self._read_form()
        except ValueError as exc:
            messagebox.showwarning("无法测试", str(exc), parent=self)
            return
        if not model.api_key:
            messagebox.showinfo("需要 API Key", "请先填写 API Key。", parent=self)
            return

        self.test_button.configure(state="disabled")
        self.status_var.set("正在测试连接...")

        def worker() -> None:
            try:
                reply = self.model_client.test_connection(model)
                self.after(0, lambda: self._finish_test(f"连接成功：{reply[:120]}"))
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish_test(f"连接失败：{error}"))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_test(self, message: str) -> None:
        self.test_button.configure(state="normal")
        self.status_var.set(message)


def main() -> None:
    app = ProjectAssistantApp()
    app.mainloop()
