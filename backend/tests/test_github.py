from auth.store import upsert_github_connection
from auth.token_crypto import encrypt_secret
from tests.conftest import register_user


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
    assert names == {"src", "app.py", "README.md"}

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


def test_github_import_rejects_path_traversal(client):
    headers = register_user(client)
    res = client.post(
        "/api/github/import",
        json={"owner": "octocat", "repo": "demo", "source_path": "../secret.py"},
        headers=headers,
    )
    assert res.status_code == 400
