def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_register(client):
    resp = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "Secure@Pass123",
        "name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["role"] == "admin"


def test_register_duplicate(client):
    client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "Secure@Pass123",
        "name": "User",
    })
    resp = client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "Secure@Pass123",
        "name": "User 2",
    })
    assert resp.status_code == 409


def test_login(client):
    client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "Secure@Pass123",
        "name": "Login User",
    })
    resp = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "Secure@Pass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "wrong@example.com",
        "password": "Secure@Pass123",
        "name": "User",
    })
    resp = client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_me(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_me_no_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


def test_register_short_password(client):
    resp = client.post("/api/auth/register", json={
        "email": "short@example.com",
        "password": "abc",
        "name": "User",
    })
    assert resp.status_code == 422
