"""Shared test fixtures."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from auth.store import init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "auth.db"
    monkeypatch.setattr("auth.store.AUTH_DB_PATH", db_path)
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def register_user(client: TestClient, username: str | None = None, password: str = "password123") -> dict[str, str]:
    name = username or f"user_{uuid.uuid4().hex[:12]}"
    res = client.post("/api/auth/register", json={"username": name, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
