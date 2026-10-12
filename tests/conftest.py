import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """У каждого теста своя чистая база и лимит 5/мин: настоящий triage.db не трогаем."""
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "5")
    store.init_db(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def client():
    return TestClient(app)


GOOD = {"text": "Не пришёл чек после оплаты", "channel": "form", "client_id": "c1"}
