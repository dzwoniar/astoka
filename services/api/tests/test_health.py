"""Smoke tests for /health endpoints (Sprint 0 — verifies app boots)."""

from fastapi.testclient import TestClient

from astoka_api.main import app


def test_health_live() -> None:
    with TestClient(app) as client:
        resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_full_returns_dependency_list() -> None:
    """Full health probe returns dep list. In CI without infra all deps will be down,
    which is fine — we only assert structure here, not status."""
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "version" in body
    dep_names = {d["name"] for d in body["dependencies"]}
    assert dep_names == {"postgres", "redis", "minio", "ollama"}
