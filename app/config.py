"""Настройки из env и правила из config/triage.yaml."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

load_dotenv(ROOT / ".env")


class ConfigError(RuntimeError):
    """Не хватает обязательной настройки (например, ключа)."""


@dataclass(frozen=True)
class Rules:
    categories: list[str]
    confidences: list[str]
    max_reply_sentences: int
    model_timeout_seconds: int
    fallback_reply: str
    fallback_category: str
    prompt_template: str
    knowledge: str


def load_rules() -> Rules:
    data = yaml.safe_load((CONFIG_DIR / "triage.yaml").read_text(encoding="utf-8"))
    return Rules(
        categories=data["categories"],
        confidences=data["confidences"],
        max_reply_sentences=data["max_reply_sentences"],
        model_timeout_seconds=data["model_timeout_seconds"],
        fallback_reply=data["fallback_reply"],
        fallback_category=data["fallback_category"],
        prompt_template=(CONFIG_DIR / "prompt.md").read_text(encoding="utf-8"),
        knowledge=(CONFIG_DIR / "knowledge.md").read_text(encoding="utf-8").strip(),
    )


def api_key() -> str:
    key = os.getenv("PROXY_API_KEY", "").strip()
    if not key:
        raise ConfigError("Не задан PROXY_API_KEY. Скопируйте .env.example в .env и впишите ключ ProxyAPI.")
    return key


def base_url() -> str:
    return os.getenv("PROXY_API_BASE_URL", "https://api.proxyapi.ru/anthropic")


def model_name() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
