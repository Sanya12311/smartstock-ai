from unittest.mock import patch

STARTING_BALANCE = 1_000_000.0


def _mock_price(price, status="live"):
    return patch("app.services.paper_trading_service.stock_service.resolve_current_price", return_value=(price, status))


def test_account_lazily_created_with_starting_balance(client, auth_headers):
    response = client.get("/paper/account", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == STARTING_BALANCE
    assert body["net_worth"] == STARTING_BALANCE
    assert body["holdings"] == []


def test_buy_without_price_is_honestly_rejected(client, auth_headers, seeded_stock):
    with _mock_price(None, status="unavailable"):
        response = client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 5})
    assert response.status_code == 201  # request accepted, execution rejected
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["price"] is None
    assert "price" in body["rejection_reason"].lower()


def test_buy_success_deducts_balance(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        response = client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETE"

    account = client.get("/paper/account", headers=auth_headers).json()
    assert account["balance"] == STARTING_BALANCE - 30000.0


def test_repeat_buy_uses_weighted_average_cost(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})
    with _mock_price(3400.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})

    with _mock_price(3400.0):
        account = client.get("/paper/account", headers=auth_headers).json()

    holding = account["holdings"][0]
    assert holding["quantity"] == 20
    assert holding["avg_buy_price"] == 3200.0  # (10*3000 + 10*3400) / 20


def test_buy_exceeding_balance_rejected(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        response = client.post(
            "/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 1_000_000}
        )
    assert response.json()["status"] == "REJECTED"
    assert "insufficient" in response.json()["rejection_reason"].lower()


def test_sell_more_than_held_rejected(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        response = client.post("/paper/orders/sell", headers=auth_headers, json={"symbol": "TCS", "quantity": 5})
    assert response.json()["status"] == "REJECTED"
    assert "insufficient" in response.json()["rejection_reason"].lower()


def test_sell_reduces_holding_without_changing_avg_cost(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 20})
    with _mock_price(3400.0):
        client.post("/paper/orders/sell", headers=auth_headers, json={"symbol": "TCS", "quantity": 5})

    with _mock_price(3400.0):
        account = client.get("/paper/account", headers=auth_headers).json()

    holding = account["holdings"][0]
    assert holding["quantity"] == 15
    assert holding["avg_buy_price"] == 3000.0  # unchanged by the sell


def test_selling_entire_position_removes_holding(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})
        client.post("/paper/orders/sell", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})

    account = client.get("/paper/account", headers=auth_headers).json()
    assert account["holdings"] == []


def test_net_worth_reflects_realized_and_unrealized_pnl(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 20})
    with _mock_price(3400.0):
        client.post("/paper/orders/sell", headers=auth_headers, json={"symbol": "TCS", "quantity": 5})
        account = client.get("/paper/account", headers=auth_headers).json()

    # balance = 1,000,000 - 60,000 + 17,000 = 957,000
    assert account["balance"] == 957000.0
    # holdings_value = 15 * 3400 = 51,000
    assert account["holdings_value"] == 51000.0
    assert account["net_worth"] == 1008000.0
    assert account["total_pnl"] == 8000.0


def test_order_history_lists_all_orders_including_rejected(client, auth_headers, seeded_stock):
    with _mock_price(3000.0):
        client.post("/paper/orders/buy", headers=auth_headers, json={"symbol": "TCS", "quantity": 10})
    with _mock_price(3000.0):
        client.post("/paper/orders/sell", headers=auth_headers, json={"symbol": "TCS", "quantity": 999})

    orders = client.get("/paper/orders", headers=auth_headers).json()
    assert len(orders) == 2
    statuses = {o["status"] for o in orders}
    assert statuses == {"COMPLETE", "REJECTED"}


def test_paper_endpoints_require_auth(client):
    assert client.get("/paper/account").status_code == 401
    assert client.post("/paper/orders/buy", json={"symbol": "TCS", "quantity": 1}).status_code == 401
