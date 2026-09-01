def test_login_rate_limited_after_repeated_attempts(client, test_user):
    for _ in range(5):
        response = client.post(
            "/auth/login", data={"username": test_user.email, "password": "WrongPassword"}
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "WrongPassword"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_login_rate_limit_does_not_block_a_different_endpoint(client, test_user):
    for _ in range(5):
        client.post("/auth/login", data={"username": test_user.email, "password": "WrongPassword"})

    # /auth/me has its own dependency chain and isn't behind the login rate limiter
    response = client.get("/auth/me")
    assert response.status_code == 401  # unauthenticated, not 429


def test_register_rate_limited_after_repeated_attempts(client):
    for i in range(5):
        response = client.post(
            "/auth/register",
            json={"email": f"ratelimit{i}@example.com", "full_name": "RL", "password": "TestPass123"},
        )
        assert response.status_code == 201

    response = client.post(
        "/auth/register",
        json={"email": "onemore@example.com", "full_name": "RL", "password": "TestPass123"},
    )
    assert response.status_code == 429


def test_successful_login_still_counts_toward_the_limit(client, test_user):
    for _ in range(5):
        response = client.post(
            "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
        )
        assert response.status_code == 200

    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
    )
    assert response.status_code == 429
