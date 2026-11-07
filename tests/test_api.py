
import pytest
from fastapi.testclient import TestClient

from src import app as service

KEY = {"X-API-Key": "test-api-key"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-api-key")
    service.rate_history.clear()
    service.auth_failures.clear()

    with TestClient(service.app) as c:
        yield c


def test_health(client):
    assert client.get("/health").status_code == 200


def test_page(client):
    assert client.get("/").status_code == 200


def test_predict(client):
    response = client.post(
        "/predict",
        json={"text": "What is machine learning?"},
        headers=KEY
    )
    assert response.status_code == 200
    assert response.json()["prediction"] in ("BENIGN", "INJECTION")


def test_missing_token(client):
    assert client.post("/predict", json={"text": "hello"}).status_code == 401


def test_invalid_token(client):
    response = client.post(
        "/predict", json={"text": "hello"},
        headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 401


def test_empty(client):
    assert client.post(
        "/predict", json={"text": " "}, headers=KEY
    ).status_code == 422


def test_wrong_type(client):
    assert client.post(
        "/predict", json={"text": 123}, headers=KEY
    ).status_code == 422


def test_too_long(client):
    assert client.post(
        "/predict", json={"text": "a" * 10001}, headers=KEY
    ).status_code == 413


def test_body_size(client):
    response = client.post(
        "/predict",
        content="a" * 32769,
        headers={**KEY, "Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_bad_json(client):
    response = client.post(
        "/predict",
        content="[",
        headers={**KEY, "Content-Type": "application/json"}
    )
    assert response.status_code == 400


def test_unsupported_type(client):
    response = client.post(
        "/predict",
        content="hi",
        headers={**KEY, "Content-Type": "text/plain"}
    )
    assert response.status_code == 415


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(service, "RATE_LIMIT", 2)

    for _ in range(2):
        assert client.post(
            "/predict", json={"text": "hello"}, headers=KEY
        ).status_code == 200

    assert client.post(
        "/predict", json={"text": "hello"}, headers=KEY
    ).status_code == 429


def test_metrics_protected(client):
    assert client.get("/metrics").status_code == 401
    assert "ml_api_requests_total" in client.get(
        "/metrics", headers=KEY
    ).text


def test_bad_model_hash(monkeypatch, tmp_path):
    monkeypatch.setenv("API_TOKEN", "test-api-key")

    bad_hash = tmp_path / "baseline.sha256"
    bad_hash.write_text("0" * 64 + "  baseline.joblib\n")

    monkeypatch.setattr(service, "hash_file", bad_hash)

    with TestClient(service.app) as client:
        assert client.get("/health").status_code == 503

