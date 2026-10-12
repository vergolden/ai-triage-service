import pytest
from sqlalchemy import select

from app import llm, store
from tests.conftest import GOOD


def model_says(category="billing", confidence="high", reply="Чек придёт на e-mail."):
    return lambda *a, **k: {"category": category, "draft_reply": reply, "confidence": confidence}


def all_tickets():
    with store.session() as db:
        return db.scalars(select(store.Ticket).order_by(store.Ticket.id)).all()


# --- правила эскалации (критерий 6) ---

@pytest.mark.parametrize("category,confidence,expected", [
    ("complaint", "high", True),
    ("billing", "low", True),
    ("complaint", "low", True),
    ("billing", "high", False),
    ("support", "medium", False),
    ("other", "high", False),
])
def test_escalation_rules(client, monkeypatch, category, confidence, expected):
    monkeypatch.setattr(llm, "ask_model", model_says(category, confidence))
    assert client.post("/triage", json=GOOD).json()["escalate"] is expected


# --- запись в tickets (критерии 2, 3, 5) ---

def test_accepted_request_is_saved(client, monkeypatch):
    monkeypatch.setattr(llm, "ask_model", model_says("support", "medium"))
    client.post("/triage", json=GOOD)
    (t,) = all_tickets()
    assert (t.client_id, t.channel, t.text) == ("c1", "form", GOOD["text"])
    assert (t.category, t.confidence, t.escalate, t.error) == ("support", "medium", False, "")
    assert t.created_at is not None and t.latency_ms >= 0


def test_model_failure_is_saved_with_error(client, monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("таймаут")
    monkeypatch.setattr(llm, "ask_model", boom)
    client.post("/triage", json=GOOD)
    (t,) = all_tickets()
    assert t.escalate is True and "таймаут" in t.error


def test_invalid_request_is_not_saved(client):
    assert client.post("/triage", json={**GOOD, "text": ""}).status_code == 422
    assert store.count_tickets() == 0


# --- лимит (критерий 4) ---

def test_sixth_request_gets_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(llm, "ask_model", model_says())
    for _ in range(5):
        assert client.post("/triage", json=GOOD).status_code == 200
    r = client.post("/triage", json=GOOD)
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 60
    assert store.count_tickets() == 5  # отказ в базу не пишется


def test_other_client_is_not_affected(client, monkeypatch):
    monkeypatch.setattr(llm, "ask_model", model_says())
    for _ in range(5):
        client.post("/triage", json=GOOD)
    assert client.post("/triage", json=GOOD).status_code == 429
    assert client.post("/triage", json={**GOOD, "client_id": "c2"}).status_code == 200


def test_limit_value_comes_from_env(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setattr(llm, "ask_model", model_says())
    assert [client.post("/triage", json=GOOD).status_code for _ in range(3)] == [200, 200, 429]


def test_model_failures_count_toward_limit(client, monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("сбой")
    monkeypatch.setattr(llm, "ask_model", boom)
    for _ in range(5):
        assert client.post("/triage", json=GOOD).status_code == 200
    assert client.post("/triage", json=GOOD).status_code == 429


def test_window_slides_old_tickets_do_not_count(client, monkeypatch):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setattr(llm, "ask_model", model_says())
    old = datetime.now(timezone.utc) - timedelta(seconds=90)
    with store.session() as db:
        for _ in range(5):
            db.add(store.Ticket(created_at=old, client_id="c1", channel="form", text="x", category="other",
                                draft_reply="x", confidence="high", escalate=False, error="", model="", latency_ms=0))
        db.commit()
    assert client.post("/triage", json=GOOD).status_code == 200  # записи 90 секунд назад вне окна
