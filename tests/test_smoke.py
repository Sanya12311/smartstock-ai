def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_client_uses_isolated_test_db(client, test_user):
    # If this were hitting the real dev DB, this user wouldn't exist there.
    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
    )
    assert response.status_code == 200
