from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .models import AppConfig, ModelConfig


CONFIG_VERSION = 1
ENC_PREFIX = "xor1:"


class SecretCodec:
    """Small local-only secret codec for config-at-rest.

    This avoids storing raw API keys in config.json. It is not a replacement
    for an OS keychain, but keeps casual file reads from exposing the key.
    """

    def __init__(self) -> None:
        seed = "|".join(
            [
                getpass.getuser(),
                str(Path.home()),
                os.environ.get("COMPUTERNAME", ""),
            ]
        )
        self._key = hashlib.sha256(seed.encode("utf-8")).digest()

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        raw = value.encode("utf-8")
        mixed = bytes(byte ^ self._key[index % len(self._key)] for index, byte in enumerate(raw))
        return ENC_PREFIX + base64.urlsafe_b64encode(mixed).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith(ENC_PREFIX):
            return value
        payload = value[len(ENC_PREFIX) :]
        try:
            raw = base64.urlsafe_b64decode(payload.encode("ascii"))
            plain = bytes(byte ^ self._key[index % len(self._key)] for index, byte in enumerate(raw))
            return plain.decode("utf-8")
        except Exception:
            return ""


class ConfigStore:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or Path(os.environ.get("PROJECT_ASSISTANT_HOME", Path.home() / ".project-assistant"))
        self.config_path = self.data_dir / "config.json"
        self.codec = SecretCodec()

    def load(self) -> AppConfig:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            config = self._default_config()
            self.save(config)
            return config

        with self.config_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return self._deserialize(raw)

    def save(self, config: AppConfig) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = self._serialize(config)
        tmp_path = self.config_path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp_path.replace(self.config_path)

    def upsert_model(self, config: AppConfig, model: ModelConfig) -> None:
        for index, existing in enumerate(config.models):
            if existing.id == model.id:
                config.models[index] = model
                break
        else:
            config.models.append(model)
        config.selected_model_id = model.id
        self.save(config)

    def delete_model(self, config: AppConfig, model_id: str) -> None:
        config.models = [model for model in config.models if model.id != model_id]
        if config.selected_model_id == model_id:
            config.selected_model_id = config.models[0].id if config.models else None
        self.save(config)

    def set_selected_model(self, config: AppConfig, model_id: str) -> None:
        config.selected_model_id = model_id
        self.save(config)

    def set_project_dir(self, config: AppConfig, project_dir: str) -> None:
        config.project_dir = project_dir
        self.save(config)

    def _default_config(self) -> AppConfig:
        project_dir = str(Path.cwd() / "projects")
        models = [
            ModelConfig(
                name="DeepSeek",
                model_name="deepseek-chat",
                base_url="https://api.deepseek.com",
                temperature=0.3,
                max_tokens=4096,
            ),
            ModelConfig(
                name="OpenAI Compatible",
                model_name="gpt-4o-mini",
                base_url="https://api.openai.com/v1",
                temperature=0.3,
                max_tokens=4096,
            ),
            ModelConfig(
                name="Local OpenAI Compatible",
                model_name="local-model",
                base_url="http://127.0.0.1:11434/v1",
                temperature=0.3,
                max_tokens=4096,
            ),
        ]
        return AppConfig(project_dir=project_dir, selected_model_id=models[0].id, models=models)

    def _serialize(self, config: AppConfig) -> Dict[str, object]:
        return {
            "version": CONFIG_VERSION,
            "project_dir": config.project_dir,
            "selected_model_id": config.selected_model_id,
            "theme": config.theme,
            "history_window": config.history_window,
            "models": [self._serialize_model(model) for model in config.models],
        }

    def _serialize_model(self, model: ModelConfig) -> Dict[str, object]:
        payload = model.to_dict(include_api_key=False)
        payload["encrypted_api_key"] = self.codec.encrypt(model.api_key)
        return payload

    def _deserialize(self, raw: Dict[str, object]) -> AppConfig:
        models_raw = raw.get("models") if isinstance(raw.get("models"), list) else []
        models: List[ModelConfig] = [self._deserialize_model(item) for item in models_raw if isinstance(item, dict)]
        if not models:
            models = self._default_config().models

        selected_model_id = raw.get("selected_model_id")
        if not isinstance(selected_model_id, str) or not any(model.id == selected_model_id for model in models):
            selected_model_id = models[0].id

        project_dir = raw.get("project_dir")
        if not isinstance(project_dir, str) or not project_dir.strip():
            project_dir = str(Path.cwd() / "projects")

        return AppConfig(
            project_dir=project_dir,
            selected_model_id=selected_model_id,
            theme=str(raw.get("theme") or "light"),
            history_window=int(raw.get("history_window") or 8),
            models=models,
        )

    def _deserialize_model(self, raw: Dict[str, object]) -> ModelConfig:
        data = dict(raw)
        encrypted_key = data.pop("encrypted_api_key", "")
        if isinstance(encrypted_key, str):
            data["api_key"] = self.codec.decrypt(encrypted_key)
        return ModelConfig.from_dict(data)
