import json

import pytest

from app import llm
from app.config import ConfigError
from tests.conftest import GOOD

REPLY = json.dumps({"category": "support", "draft_reply": "Перенос занятия делается в личном кабинете.", "confidence": "high"})


def test_openai_is_default(client, monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    calls = []
    monkeypatch.setattr(llm, "_ask_openai", lambda *a: calls.append("openai") or REPLY)
    monkeypatch.setattr(llm, "_ask_anthropic", lambda *a: calls.append("anthropic") or REPLY)
    assert client.post("/triage", json=GOOD).status_code == 200
    assert calls == ["openai"]


def test_switch_to_anthropic(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    calls = []
    monkeypatch.setattr(llm, "_ask_openai", lambda *a: calls.append("openai") or REPLY)
    monkeypatch.setattr(llm, "_ask_anthropic", lambda *a: calls.append("anthropic") or REPLY)
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200 and r.json()["category"] == "support"
    assert calls == ["anthropic"]


def test_unknown_provider_gives_fallback(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200 and r.json()["escalate"] is True


@pytest.mark.parametrize("raw", ["не json", "[1, 2]", ""])
def test_non_json_from_provider_gives_fallback(client, monkeypatch, raw):
    monkeypatch.setattr(llm, "_ask_openai", lambda *a: raw)
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200 and r.json()["escalate"] is True


def test_provider_value_validated(monkeypatch):
    from app import config
    monkeypatch.setenv("LLM_PROVIDER", "x")
    with pytest.raises(ConfigError):
        config.provider()
