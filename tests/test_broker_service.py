from unittest.mock import patch

from app.models.broker_account import BrokerAccount
from app.services import broker_service
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


def test_get_holdings_uses_connected_users_own_credentials(db_session, test_user):
    _connected_broker(db_session, test_user)

    with patch.object(broker_service.broker, "get_holdings") as mock_get_holdings:
        mock_get_holdings.return_value = [
            {
                "exchange": "NSE",
                "trading_symbol": "TCS",
                "security_id": "11536",
                "isin": "INE467B01029",
                "total_qty": 10,
                "dp_qty": 10,
                "t1_qty": 0,
                "available_qty": 10,
                "collateral_qty": 0,
                "avg_cost_price": 3800.0,
            }
        ]
        holdings = broker_service.get_holdings(db_session, test_user)

    mock_get_holdings.assert_called_once_with("FAKE_ACCESS_TOKEN", "DHAN_TEST_999")
    assert holdings[0]["trading_symbol"] == "TCS"


def test_get_funds_uses_connected_users_own_credentials(db_session, test_user):
    _connected_broker(db_session, test_user)

    with patch.object(broker_service.broker, "get_fund_limits") as mock_get_funds:
        mock_get_funds.return_value = {"withdrawable_balance": 50000.0}
        funds = broker_service.get_funds(db_session, test_user)

    mock_get_funds.assert_called_once_with("FAKE_ACCESS_TOKEN", "DHAN_TEST_999")
    assert funds["withdrawable_balance"] == 50000.0


def test_get_holdings_without_connected_broker_rejected(db_session, test_user):
    try:
        broker_service.get_holdings(db_session, test_user)
        assert False, "should have raised"
    except ValueError as exc:
        assert "broker" in str(exc).lower()


def test_broker_holdings_api_requires_auth(client):
    assert client.get("/broker/holdings").status_code == 401
    assert client.get("/broker/funds").status_code == 401


def test_broker_holdings_api_without_connected_broker_returns_400(client, auth_headers):
    response = client.get("/broker/holdings", headers=auth_headers)
    assert response.status_code == 400
