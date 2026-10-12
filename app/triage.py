"""Ядро: собрать промпт, спросить модель, проверить ответ. Без знания про HTTP и базу."""
import logging
import re

from app import llm
from app.config import Rules, ConfigError
from app.schemas import TriageRequest, TriageResponse

log = logging.getLogger("triage.core")


def build_system_prompt(rules: Rules) -> str:
    # .replace, а не .format: в тексте справки могут встретиться фигурные скобки
    return rules.prompt_template.replace("{knowledge}", rules.knowledge)


def count_sentences(text: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?…])\s+", text.strip()) if part])


def fallback(rules: Rules, reason: str) -> tuple[TriageResponse, str]:
    """Ответ на случай сбоя: клиент не остаётся без ответа, человек подключается."""
    return TriageResponse(
        category=rules.fallback_category, draft_reply=rules.fallback_reply, confidence="low", escalate=True
    ), reason


def find_injection(text: str, rules: Rules) -> str | None:
    """Шаблон из triage.yaml, под который подпало обращение, или None."""
    for pattern in rules.injection_patterns:
        if pattern.search(text):
            return pattern.pattern
    return None


def run_triage(request: TriageRequest, rules: Rules) -> tuple[TriageResponse, str]:
    """Возвращает (ответ клиенту, пометка или ошибка; пустая строка, если всё штатно)."""
    pattern = find_injection(request.text, rules)
    if pattern:
        # модель не вызываем: явную атаку не отправляем во внешний сервис и не тратим токены
        log.warning("Подозрение на манипуляцию, шаблон: %s", pattern)
        return fallback(rules, f"Подозрение на манипуляцию (шаблон: {pattern})")
    try:
        data = llm.ask_model(
            build_system_prompt(rules), request.text, rules.categories, rules.confidences,
            rules.model_timeout_seconds,
        )
    except (llm.LLMError, ConfigError) as exc:
        log.warning("Сбой модели: %s", exc)
        return fallback(rules, str(exc))

    category, reply, confidence = data.get("category"), data.get("draft_reply"), data.get("confidence")
    if category not in rules.categories or confidence not in rules.confidences:
        return fallback(rules, "Недопустимые значения в ответе модели")
    if not isinstance(reply, str) or not reply.strip():
        return fallback(rules, "Пустой черновик ответа")
    if count_sentences(reply) > rules.max_reply_sentences:
        return fallback(rules, f"Черновик длиннее {rules.max_reply_sentences} предложений")

    escalate = category in rules.escalate_categories or confidence in rules.escalate_confidences
    return TriageResponse(category=category, draft_reply=reply.strip(), confidence=confidence, escalate=escalate), ""
