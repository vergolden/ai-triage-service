import pytest

from app import llm
from tests.conftest import GOOD


def fake_model(category="billing", reply="Чек придёт на e-mail сразу после оплаты.", confidence="high"):
    def _ask(*args, **kwargs):
        return {"category": category, "draft_reply": reply, "confidence": confidence}
    return _ask


def test_good_request_returns_contract(client, monkeypatch):
    monkeypatch.setattr(llm, "ask_model", fake_model())
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"category", "draft_reply", "confidence", "escalate"}
    assert body["category"] == "billing" and body["confidence"] == "high"


@pytest.mark.parametrize("patch", [
    {"text": ""},
    {"text": "   "},
    {"text": "а" * 2001},
    {"channel": "sms"},
    {"client_id": ""},
    {"client_id": "x" * 65},
])
def test_bad_input_gives_422(client, patch):
    r = client.post("/triage", json={**GOOD, **patch})
    assert r.status_code == 422


@pytest.mark.parametrize("missing", ["text", "channel", "client_id"])
def test_missing_field_gives_422(client, missing):
    payload = {k: v for k, v in GOOD.items() if k != missing}
    assert client.post("/triage", json=payload).status_code == 422


def test_boundary_2000_chars_ok(client, monkeypatch):
    monkeypatch.setattr(llm, "ask_model", fake_model())
    assert client.post("/triage", json={**GOOD, "text": "а" * 2000}).status_code == 200


def test_model_failure_gives_fallback(client, monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("таймаут")
    monkeypatch.setattr(llm, "ask_model", boom)
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200
    assert r.json()["escalate"] is True
    assert "оператор" in r.json()["draft_reply"]


@pytest.mark.parametrize("bad", [
    {"category": "spam", "draft_reply": "Текст.", "confidence": "high"},
    {"category": "billing", "draft_reply": "", "confidence": "high"},
    {"category": "billing", "draft_reply": "Текст.", "confidence": "sure"},
    {"category": "billing", "draft_reply": "Раз. Два. Три. Четыре. Пять. Шесть. Семь.", "confidence": "high"},
    {},
])
def test_bad_model_output_gives_fallback(client, monkeypatch, bad):
    monkeypatch.setattr(llm, "ask_model", lambda *a, **k: bad)
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200 and r.json()["escalate"] is True


def test_no_api_key_gives_fallback_not_crash(client, monkeypatch):
    monkeypatch.delenv("PROXY_API_KEY", raising=False)
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 200 and r.json()["escalate"] is True
