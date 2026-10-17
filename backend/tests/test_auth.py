from tests.conftest import register_user


def test_register_login_and_me(client):
    headers = register_user(client, username="alice_tester", password="password123")
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice_tester"
    assert me.json()["auth_provider"] == "local"

    login = client.post(
        "/api/auth/login",
        json={"username": "alice_tester", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_duplicate_username_rejected(client):
    register_user(client, username="bob_unique", password="password123")
    dup = client.post(
        "/api/auth/register",
        json={"username": "bob_unique", "password": "otherpass99"},
    )
    assert dup.status_code == 409


def test_login_wrong_password(client):
    register_user(client, username="carol_user", password="password123")
    bad = client.post(
        "/api/auth/login",
        json={"username": "carol_user", "password": "wrongpassword"},
    )
    assert bad.status_code == 401


def test_sessions_require_auth(client):
    res = client.get("/api/sessions")
    assert res.status_code == 401
