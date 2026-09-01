def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "full_name": "New User", "password": "TestPass123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client, test_user):
    response = client.post(
        "/auth/register",
        json={"email": test_user.email, "full_name": "Dup", "password": "TestPass123"},
    )
    assert response.status_code == 400


def test_register_password_too_short_rejected(client):
    response = client.post(
        "/auth/register",
        json={"email": "short@example.com", "full_name": "Short", "password": "1234"},
    )
    assert response.status_code == 422


def test_register_invalid_email_rejected(client):
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "full_name": "Bad Email", "password": "TestPass123"},
    )
    assert response.status_code == 422


def test_password_is_hashed_not_stored_plain(db_session, client):
    client.post(
        "/auth/register",
        json={"email": "hashcheck@example.com", "full_name": "Hash Check", "password": "TestPass123"},
    )
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "hashcheck@example.com").first()
    assert user.hashed_password != "TestPass123"
    assert user.hashed_password.startswith("$2b$")  # bcrypt hash prefix


def test_login_success(client, test_user):
    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client, test_user):
    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "WrongPassword"}
    )
    assert response.status_code == 401


def test_login_unknown_email_rejected(client):
    response = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "TestPass123"}
    )
    assert response.status_code == 401


def test_protected_route_requires_auth(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_with_valid_token(client, auth_headers, test_user):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


def test_protected_route_with_garbage_token_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_logout_requires_auth(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_logout_with_valid_token(client, auth_headers):
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200
