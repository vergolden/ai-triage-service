"""Единственное место, которое знает про ProxyAPI и Claude."""
import json
import logging

import anthropic

from app import config

log = logging.getLogger("triage.llm")


class LLMError(RuntimeError):
    """Модель недоступна, ответила ошибкой или вернула не то."""


def _schema(categories: list[str], confidences: list[str]) -> dict:
    # API гарантирует структуру и допустимые значения. Длину текста (1-6 предложений) схема
    # не проверяет - её контролирует код в triage.py.
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": categories},
            "draft_reply": {"type": "string"},
            "confidence": {"type": "string", "enum": confidences},
        },
        "required": ["category", "draft_reply", "confidence"],
        "additionalProperties": False,
    }


def ask_model(system: str, text: str, categories: list[str], confidences: list[str], timeout: int) -> dict:
    """Отправляет обращение модели, возвращает разобранный JSON. При любой проблеме - LLMError."""
    client = anthropic.Anthropic(
        api_key=config.api_key(), base_url=config.base_url(), timeout=timeout, max_retries=1
    )
    try:
        response = client.messages.create(
            model=config.model_name(),
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": f"Обращение клиента:\n\n{text}"}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": _schema(categories, confidences)},
            },
        )
    except anthropic.APIError as exc:
        raise LLMError(f"Ошибка API: {type(exc).__name__}") from exc

    # Модель может вернуть блок рассуждения перед текстом - берём только текстовые блоки.
    raw = "".join(block.text for block in response.content if block.type == "text")
    log.info("Ответ модели: %d симв., токены вход/выход %s/%s, остановка %s", len(raw),
             response.usage.input_tokens, response.usage.output_tokens, response.stop_reason)
    if response.stop_reason == "max_tokens":
        raise LLMError("Ответ обрезан по лимиту токенов")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError("Модель вернула не JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("Модель вернула JSON не того вида")
    return data
