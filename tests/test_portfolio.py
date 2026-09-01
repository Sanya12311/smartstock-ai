from unittest.mock import patch

from app.services import portfolio_service


def _mock_price(price, status="live"):
    """portfolio_service calls stock_service.resolve_current_price(stock) -> (price, status)."""
    return patch("app.services.portfolio_service.stock_service.resolve_current_price", return_value=(price, status))


def test_add_and_list_holding(client, auth_headers, seeded_stock):
    response = client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == "TCS"
    assert body["invested_amount"] == 30000.0


def test_add_holding_unknown_symbol_rejected(client, auth_headers):
    response = client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "FAKESYM", "quantity": 10, "buy_price": 100, "buy_date": "2026-01-15"},
    )
    assert response.status_code == 404


def test_empty_portfolio_shows_zero_not_unavailable(client, auth_headers):
    """Regression test: an empty portfolio must show ₹0, not '—' (unavailable) —
    those mean different things and were previously conflated (found live in Phase 17)."""
    response = client.get("/portfolio", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_invested"] == 0.0
    assert body["total_current_value"] == 0.0
    assert body["total_pnl"] == 0.0
    assert body["risk"]["risk_level"] == "unavailable"
    assert "No holdings yet" in body["risk"]["reasons"][0]


def test_portfolio_pnl_calculation_with_profit(client, auth_headers, seeded_stock):
    client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    with _mock_price(3450.0):
        response = client.get("/portfolio", headers=auth_headers)

    body = response.json()
    assert body["total_invested"] == 30000.0
    assert body["total_current_value"] == 34500.0
    assert body["total_pnl"] == 4500.0
    assert body["total_pnl_percent"] == 15.0
    assert body["prices_partial"] is False
    assert body["allocation"] == [{"symbol": "TCS", "percent": 100.0}]


def test_portfolio_pnl_calculation_with_loss(client, auth_headers, seeded_stock):
    client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    with _mock_price(2700.0):
        response = client.get("/portfolio", headers=auth_headers)

    body = response.json()
    assert body["total_pnl"] == -3000.0
    assert body["total_pnl_percent"] == -10.0


def test_portfolio_shows_unavailable_when_price_cant_be_fetched(client, auth_headers, seeded_stock):
    client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    with _mock_price(None, status="unavailable"):
        response = client.get("/portfolio", headers=auth_headers)

    body = response.json()
    assert body["total_invested"] == 30000.0
    assert body["total_current_value"] is None  # never fabricated as 0 or any guess
    assert body["holdings"][0]["price_status"] == "unavailable"


def test_delete_holding(client, auth_headers, seeded_stock):
    create = client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    holding_id = create.json()["id"]

    delete_response = client.delete(f"/portfolio/holdings/{holding_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    with _mock_price(3450.0):
        response = client.get("/portfolio", headers=auth_headers)
    assert response.json()["holdings"] == []


def test_cannot_delete_another_users_holding(client, auth_headers, seeded_stock, db_session):
    """IDOR check: a holding must not be deletable by a different user."""
    create = client.post(
        "/portfolio/holdings",
        headers=auth_headers,
        json={"symbol": "TCS", "quantity": 10, "buy_price": 3000, "buy_date": "2026-01-15"},
    )
    holding_id = create.json()["id"]

    from app.models.user import User
    from app.utils.security import hash_password

    other_user = User(
        email="otheruser@example.com",
        full_name="Other",
        hashed_password=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    other_login = client.post(
        "/auth/login", data={"username": "otheruser@example.com", "password": "TestPass123"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    delete_response = client.delete(f"/portfolio/holdings/{holding_id}", headers=other_headers)
    assert delete_response.status_code == 404


def test_portfolio_requires_auth(client):
    response = client.get("/portfolio")
    assert response.status_code == 401
