"""
Broad API endpoint coverage — auth, portfolio calcs, indicators, risk,
alerts, and paper trading each have their own dedicated, deeper test files.
This one covers the remaining routers (watchlist, alerts CRUD via HTTP,
notifications, broker, chat) with a focus on auth enforcement and the
basic request/response contract.
"""

from unittest.mock import patch


# ---------- Watchlist ----------


def test_watchlist_add_list_remove(client, auth_headers, seeded_stock):
    add = client.post("/watchlist", headers=auth_headers, json={"symbol": "TCS"})
    assert add.status_code == 201

    listing = client.get("/watchlist", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["symbol"] == "TCS"

    remove = client.delete("/watchlist/TCS", headers=auth_headers)
    assert remove.status_code == 204
    assert client.get("/watchlist", headers=auth_headers).json() == []


def test_watchlist_add_unknown_symbol_rejected(client, auth_headers):
    response = client.post("/watchlist", headers=auth_headers, json={"symbol": "FAKESYM"})
    assert response.status_code == 404


def test_watchlist_remove_nonexistent_item_404(client, auth_headers):
    response = client.delete("/watchlist/TCS", headers=auth_headers)
    assert response.status_code == 404


def test_watchlist_requires_auth(client):
    assert client.get("/watchlist").status_code == 401


# ---------- Alerts CRUD ----------


def test_alert_create_requires_threshold_for_price_type(client, auth_headers, seeded_stock):
    response = client.post(
        "/alerts", headers=auth_headers, json={"symbol": "TCS", "alert_type": "PRICE_ABOVE"}
    )
    assert response.status_code == 422


def test_alert_macd_cross_does_not_require_threshold(client, auth_headers, seeded_stock):
    response = client.post(
        "/alerts", headers=auth_headers, json={"symbol": "TCS", "alert_type": "MACD_CROSS"}
    )
    assert response.status_code == 201


def test_alert_invalid_type_rejected(client, auth_headers, seeded_stock):
    response = client.post(
        "/alerts", headers=auth_headers, json={"symbol": "TCS", "alert_type": "NOT_A_TYPE", "threshold": 1}
    )
    assert response.status_code == 422


def test_alert_list_and_delete(client, auth_headers, seeded_stock):
    create = client.post(
        "/alerts", headers=auth_headers, json={"symbol": "TCS", "alert_type": "PRICE_ABOVE", "threshold": 4000}
    )
    alert_id = create.json()["id"]

    listing = client.get("/alerts", headers=auth_headers)
    assert len(listing.json()) == 1

    delete = client.delete(f"/alerts/{alert_id}", headers=auth_headers)
    assert delete.status_code == 204
    assert client.get("/alerts", headers=auth_headers).json() == []


def test_alerts_require_auth(client):
    assert client.get("/alerts").status_code == 401


# ---------- Notifications ----------


def test_notifications_list_empty_by_default(client, auth_headers):
    response = client.get("/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_mark_nonexistent_notification_read_404(client, auth_headers):
    response = client.post("/notifications/99999/read", headers=auth_headers)
    assert response.status_code == 404


def test_notifications_require_auth(client):
    assert client.get("/notifications").status_code == 401


# ---------- Broker ----------


def test_broker_status_not_connected_by_default(client, auth_headers):
    response = client.get("/broker/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_CONNECTED"


def test_broker_connect_start_generates_unique_token(client, auth_headers):
    response = client.post("/broker/connect/start", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["connection_token"] in body["redirect_uri_to_register"]


def test_broker_credentials_unknown_token_404(client, auth_headers):
    response = client.post(
        "/broker/connect/credentials",
        headers=auth_headers,
        json={"connection_token": "nonexistent", "dhan_client_id": "X", "app_id": "Y", "app_secret": "Z"},
    )
    assert response.status_code == 404


def test_broker_requires_auth(client):
    assert client.get("/broker/status").status_code == 401


# ---------- Chat (Gemini mocked — never call the real API in tests) ----------


def test_chat_creates_session_and_returns_reply(client, auth_headers):
    with patch("app.services.chat_service.generate_explanation", return_value="Mocked AI reply."):
        response = client.post("/chat", headers=auth_headers, json={"message": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Mocked AI reply."
    assert "session_id" in body
    assert "not guaranteed financial advice" in body["disclaimer"]


def test_chat_continues_existing_session(client, auth_headers):
    with patch("app.services.chat_service.generate_explanation", return_value="First reply"):
        first = client.post("/chat", headers=auth_headers, json={"message": "Hi"})
    session_id = first.json()["session_id"]

    with patch("app.services.chat_service.generate_explanation", return_value="Second reply"):
        second = client.post(
            "/chat", headers=auth_headers, json={"message": "Follow-up", "session_id": session_id}
        )
    assert second.json()["session_id"] == session_id

    messages = client.get(f"/chat/sessions/{session_id}/messages", headers=auth_headers).json()
    assert len(messages["messages"]) == 4  # 2 user + 2 assistant


def test_chat_unknown_session_id_404(client, auth_headers):
    response = client.post("/chat", headers=auth_headers, json={"message": "Hi", "session_id": 99999})
    assert response.status_code == 404


def test_chat_requires_auth(client):
    assert client.post("/chat", json={"message": "Hi"}).status_code == 401
