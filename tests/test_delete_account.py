from unittest.mock import patch

from app.models.broker_account import BrokerAccount
from app.models.order import Order
from app.models.user import User
from app.services import order_service
from app.utils import encryption


def test_delete_account_requires_auth(client):
    response = client.post("/auth/delete-account", json={"password": "x"})
    assert response.status_code == 401


def test_delete_account_wrong_password_rejected(client, auth_headers, db_session, test_user):
    response = client.post(
        "/auth/delete-account", json={"password": "WrongPassword"}, headers=auth_headers
    )
    assert response.status_code == 400  # not 401 — see change-password's fix for why

    # user must still exist
    assert db_session.query(User).filter(User.id == test_user.id).first() is not None


def test_delete_account_success_removes_user(client, auth_headers, db_session, test_user):
    response = client.post(
        "/auth/delete-account", json={"password": "TestPass123"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert db_session.query(User).filter(User.id == test_user.id).first() is None


def test_delete_account_cascades_owned_data(client, auth_headers, db_session, test_user, seeded_stock):
    user_id = test_user.id  # captured before deletion — test_user becomes a stale/expired
    # instance once the API call's own session deletes+commits the same row underneath it.

    account = BrokerAccount(
        user_id=user_id,
        connection_token="test-token",
        status="CONNECTED",
        dhan_client_id="DHAN_TEST_999",
        access_token_encrypted=encryption.encrypt("FAKE_ACCESS_TOKEN"),
    )
    db_session.add(account)
    db_session.commit()

    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    response = client.post(
        "/auth/delete-account", json={"password": "TestPass123"}, headers=auth_headers
    )
    assert response.status_code == 200

    assert db_session.query(BrokerAccount).filter(BrokerAccount.user_id == user_id).first() is None
    assert db_session.query(Order).filter(Order.user_id == user_id).first() is None


def test_deleted_account_cannot_login(client, auth_headers, test_user):
    client.post("/auth/delete-account", json={"password": "TestPass123"}, headers=auth_headers)

    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
    )
    assert response.status_code == 401


def test_delete_account_rate_limited_after_repeated_wrong_attempts(client, auth_headers):
    for _ in range(5):
        response = client.post(
            "/auth/delete-account", json={"password": "WrongPassword"}, headers=auth_headers
        )
        assert response.status_code == 400

    response = client.post(
        "/auth/delete-account", json={"password": "WrongPassword"}, headers=auth_headers
    )
    assert response.status_code == 429
