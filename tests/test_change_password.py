def test_change_password_requires_auth(client):
    response = client.post(
        "/auth/change-password", json={"current_password": "x", "new_password": "NewPass123"}
    )
    assert response.status_code == 401


def test_change_password_wrong_current_password_rejected(client, auth_headers):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "WrongPassword", "new_password": "NewPass123"},
        headers=auth_headers,
    )
    assert response.status_code == 400  # not 401 — that would force-logout the user (see api.js)


def test_change_password_too_short_rejected(client, auth_headers):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "TestPass123", "new_password": "short"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_change_password_success_allows_login_with_new_password(client, auth_headers, test_user):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "TestPass123", "new_password": "NewPass456"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    old_login = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", data={"username": test_user.email, "password": "NewPass456"})
    assert new_login.status_code == 200


def test_change_password_rate_limited_after_repeated_wrong_attempts(client, auth_headers):
    for _ in range(5):
        response = client.post(
            "/auth/change-password",
            json={"current_password": "WrongPassword", "new_password": "NewPass123"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    response = client.post(
        "/auth/change-password",
        json={"current_password": "WrongPassword", "new_password": "NewPass123"},
        headers=auth_headers,
    )
    assert response.status_code == 429
