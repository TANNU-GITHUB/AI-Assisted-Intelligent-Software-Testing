import base64
import hashlib
import hmac
import os

from auth.store import get_github_connection, init_db, upsert_github_connection
from auth.token_crypto import encrypt_secret
from config import JWT_SECRET
from tests.conftest import register_user


def _legacy_encrypt(plain: str) -> str:
    key = hashlib.sha256(f"oauth-token:{JWT_SECRET}".encode("utf-8")).digest()
    nonce = os.urandom(16)
    data = plain.encode("utf-8")
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(byte ^ stream[index % len(stream)] for index, byte in enumerate(data))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + cipher).decode("ascii")


def test_github_url_requires_config(client, monkeypatch):
    headers = register_user(client)
    monkeypatch.setattr("auth.github_oauth.GITHUB_CLIENT_ID", "")
    res = client.get("/api/github/url", headers=headers)
    assert res.status_code == 503


def test_github_url_and_status(client, monkeypatch):
    headers = register_user(client)
    monkeypatch.setattr("auth.github_oauth.GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setattr(
        "auth.github_oauth.GITHUB_REDIRECT_URI",
        "http://localhost:3000/auth/github/callback",
    )
    res = client.get("/api/github/url", headers=headers)
    assert res.status_code == 200
    assert "github.com/login/oauth/authorize" in res.json()["url"]
    assert res.json()["state"]

    status = client.get("/api/github/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["connected"] is False


def test_github_repos_and_import(client, monkeypatch):
    headers = register_user(client)
    me = client.get("/api/auth/me", headers=headers).json()
    upsert_github_connection(
        user_id=me["id"],
        github_id="1",
        login="octocat",
        avatar_url="https://example.com/a.png",
        access_token_enc=encrypt_secret("ghs_test"),
        scope="repo",
    )

    def fake_request(_token, path, params=None):
        if path == "/user/repos":
            return [
                {
                    "id": 11,
                    "full_name": "octocat/demo",
                    "name": "demo",
                    "owner": {"login": "octocat"},
                    "private": False,
                    "description": "demo repo",
                    "default_branch": "main",
                    "language": "Python",
                    "html_url": "https://github.com/octocat/demo",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        if path == "/repos/octocat/demo/contents":
            return [
                {"name": "src", "path": "src", "type": "dir"},
                {"name": "app.py", "path": "app.py", "type": "file", "size": 20},
                {"name": "README.md", "path": "README.md", "type": "file", "size": 40},
                {"name": "image.png", "path": "image.png", "type": "file", "size": 10},
            ]
        if path == "/repos/octocat/demo/contents/app.py":
            return {
                "type": "file",
                "encoding": "base64",
                "size": 20,
                "content": "ZGVmIGFkZChhLCBiKToKICAgIHJldHVybiBhICsgYgo=",
            }
        if path == "/repos/octocat/demo/contents/README.md":
            return {
                "type": "file",
                "encoding": "base64",
                "size": 12,
                "content": "QWRkIHR3byBudW1iZXJzLg==",
            }
        raise AssertionError(path)

    monkeypatch.setattr("auth.github_routes.github_request", fake_request)

    repos = client.get("/api/github/repos", headers=headers)
    assert repos.status_code == 200
    assert repos.json()["repos"][0]["full_name"] == "octocat/demo"

    listing = client.get(
        "/api/github/contents",
        params={"owner": "octocat", "repo": "demo"},
        headers=headers,
    )
    names = {item["name"] for item in listing.json()["entries"]}
    assert names == {"src", "app.py", "README.md", "image.png"}

    imported = client.post(
        "/api/github/import",
        json={
            "owner": "octocat",
            "repo": "demo",
            "source_path": "app.py",
            "requirements_path": "README.md",
        },
        headers=headers,
    )
    assert imported.status_code == 200
    body = imported.json()
    assert "def add" in body["source_code"]
    assert "Add two numbers" in body["requirements_text"]
    assert body["filename"] == "app.py"


def test_legacy_github_token_is_upgraded_when_used(client, monkeypatch):
    headers = register_user(client)
    user = client.get("/api/auth/me", headers=headers).json()
    token = "gho_" + "legacy-token-" * 8
    upsert_github_connection(
        user_id=user["id"],
        github_id="1",
        login="octocat",
        avatar_url=None,
        access_token_enc=_legacy_encrypt(token),
        scope="repo",
    )
    monkeypatch.setattr(
        "auth.github_routes.github_request",
        lambda access_token, path, params=None: (
            [] if access_token == token and path == "/user/repos" else None
        ),
    )

    response = client.get("/api/github/repos", headers=headers)

    assert response.status_code == 200
    stored = get_github_connection(user["id"])
    assert stored is not None
    assert stored.access_token_enc.startswith("gAAAA")


def test_legacy_github_tokens_migrate_during_database_initialization(client):
    headers = register_user(client)
    user = client.get("/api/auth/me", headers=headers).json()
    upsert_github_connection(
        user_id=user["id"],
        github_id="1",
        login="octocat",
        avatar_url=None,
        access_token_enc=_legacy_encrypt("gho_" + "legacy-token-" * 8),
        scope="repo",
    )

    init_db()

    stored = get_github_connection(user["id"])
    assert stored is not None
    assert stored.access_token_enc.startswith("gAAAA")


def test_github_project_agent_runs_pipeline(client, monkeypatch):
    headers = register_user(client)
    me = client.get("/api/auth/me", headers=headers).json()
    upsert_github_connection(
        user_id=me["id"],
        github_id="1",
        login="octocat",
        avatar_url=None,
        access_token_enc=encrypt_secret("ghs_test"),
        scope="repo",
    )

    def fake_agent(**kwargs):
        assert kwargs["owner"] == "octocat"
        assert kwargs["repo"] == "demo"
        return {
            "session_id": "agentdemo",
            "status": "github_project_tested",
            "source_code": "def add(a, b):\n    return a + b\n",
            "github_agent": {"full_name": "octocat/demo", "python_files_tested": ["app.py"]},
        }

    monkeypatch.setattr("agents.github_project_agent.run_github_project_agent", fake_agent)
    res = client.post(
        "/api/github/project-agent",
        json={"owner": "octocat", "repo": "demo"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["github_agent"]["full_name"] == "octocat/demo"


def test_github_import_rejects_path_traversal(client):
    headers = register_user(client)
    res = client.post(
        "/api/github/import",
        json={"owner": "octocat", "repo": "demo", "source_path": "../secret.py"},
        headers=headers,
    )
    assert res.status_code == 400
