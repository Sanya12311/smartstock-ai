from unittest.mock import patch

from app.models.broker_account import BrokerAccount
from app.services import order_service
from app.utils import encryption


def _connected_broker(db_session, user):
    account = BrokerAccount(
        user_id=user.id,
        connection_token="test-token",
        status="CONNECTED",
        dhan_client_id="DHAN_TEST_999",
        access_token_encrypted=encryption.encrypt("FAKE_ACCESS_TOKEN"),
    )
    db_session.add(account)
    db_session.commit()
    return account


def test_export_csv_requires_auth(client):
    assert client.get("/trades/export/csv").status_code == 401


def test_export_csv_with_no_trades_is_header_only(client, auth_headers):
    response = client.get("/trades/export/csv", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]

    lines = response.text.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].split(",")[0] == "Trade ID"


def test_export_csv_includes_traded_orders(client, auth_headers, db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "TRADED"}
    ):
        order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    response = client.get("/trades/export/csv", headers=auth_headers)
    lines = response.text.strip().splitlines()
    assert len(lines) == 2
    assert "TCS" in lines[1]
    assert "TRADED" in lines[1]


def test_export_csv_excludes_pending_orders(client, auth_headers, db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    response = client.get("/trades/export/csv", headers=auth_headers)
    lines = response.text.strip().splitlines()
    assert len(lines) == 1  # header only — PENDING never reached a terminal traded state


def test_export_csv_only_includes_own_trades(client, auth_headers, db_session, test_user, seeded_stock):
    from app.models.user import User
    from app.utils.security import hash_password

    other_user = User(
        email="othertradesuser@example.com",
        full_name="Other",
        hashed_password=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    _connected_broker(db_session, other_user)

    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "TRADED"}
    ):
        order_service.place_buy_order(db_session, other_user, "TCS", 10, "MARKET")

    response = client.get("/trades/export/csv", headers=auth_headers)
    lines = response.text.strip().splitlines()
    assert len(lines) == 1  # header only — the TRADED order belongs to the other user
