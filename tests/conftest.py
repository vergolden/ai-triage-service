import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


GOOD = {"text": "Не пришёл чек после оплаты", "channel": "form", "client_id": "c1"}
