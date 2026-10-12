"""Настройки из env и правила из config/triage.yaml."""
import os
import re
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
    escalate_categories: list[str]
    escalate_confidences: list[str]
    injection_patterns: list[re.Pattern]


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
        escalate_categories=data["escalate_if"]["categories"],
        escalate_confidences=data["escalate_if"]["confidences"],
        injection_patterns=[re.compile(p, re.IGNORECASE) for p in data["injection_patterns"]],
    )


def provider() -> str:
    value = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if value not in ("openai", "anthropic"):
        raise ConfigError(f"LLM_PROVIDER={value!r} не поддерживается. Допустимо: openai, anthropic.")
    return value


def temperature() -> float:
    return float(os.getenv("LLM_TEMPERATURE", "0.2"))


def openai_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def api_key() -> str:
    key = os.getenv("PROXY_API_KEY", "").strip()
    if not key:
        raise ConfigError("Не задан PROXY_API_KEY. Скопируйте .env.example в .env и впишите ключ ProxyAPI.")
    return key


def base_url() -> str:
    return os.getenv("PROXY_API_BASE_URL", "https://api.proxyapi.ru/anthropic")


def model_name() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")


def rate_limit_per_minute() -> int:
    return int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./triage.db")
