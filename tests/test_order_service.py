from unittest.mock import patch

from app.brokers.dhan_broker import DhanBrokerError
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


def test_order_type_validation():
    from app.services.order_service import OrderValidationError, _validate_order_shape

    try:
        _validate_order_shape(10, "STOP_LOSS", None)
        assert False, "should have raised"
    except OrderValidationError as exc:
        assert "order_type" in str(exc)


def test_limit_order_without_price_rejected():
    from app.services.order_service import OrderValidationError, _validate_order_shape

    try:
        _validate_order_shape(10, "LIMIT", None)
        assert False, "should have raised"
    except OrderValidationError as exc:
        assert "price" in str(exc).lower()


def test_zero_quantity_rejected():
    from app.services.order_service import OrderValidationError, _validate_order_shape

    try:
        _validate_order_shape(0, "MARKET", None)
        assert False, "should have raised"
    except OrderValidationError as exc:
        assert "quantity" in str(exc)


def test_market_closed_blocks_order(db_session, test_user, seeded_stock):
    with patch("app.services.order_service.is_market_open", return_value=False):
        try:
            order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")
            assert False, "should have raised"
        except order_service.OrderValidationError as exc:
            assert "closed" in str(exc).lower()


def test_no_connected_broker_blocks_order(db_session, test_user, seeded_stock):
    with patch("app.services.order_service.is_market_open", return_value=True):
        try:
            order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")
            assert False, "should have raised"
        except order_service.OrderValidationError as exc:
            assert "broker" in str(exc).lower()


def test_unknown_symbol_blocks_order(db_session, test_user):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True):
        try:
            order_service.place_buy_order(db_session, test_user, "FAKESYM", 10, "MARKET")
            assert False, "should have raised"
        except order_service.OrderValidationError as exc:
            assert "not found" in str(exc).lower()


def test_successful_order_uses_connected_users_own_credentials(db_session, test_user, seeded_stock):
    """Critical: must use the CONNECTED USER's decrypted token/client_id,
    never our app-level Dhan settings — this is what makes it a real trade
    on the correct account."""
    _connected_broker(db_session, test_user)

    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order"
    ) as mock_place:
        mock_place.return_value = {"order_id": "ORDER123", "order_status": "PENDING"}
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    call_kwargs = mock_place.call_args.kwargs
    assert call_kwargs["access_token"] == "FAKE_ACCESS_TOKEN"
    assert call_kwargs["client_id"] == "DHAN_TEST_999"
    assert call_kwargs["security_id"] == "11536"
    assert call_kwargs["product_type"] == "CNC"
    assert order.status == "PENDING"
    assert order.broker_order_id == "ORDER123"
    assert order.broker_name == "DHAN"


def test_broker_rejection_recorded_with_reason(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)

    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order"
    ) as mock_place:
        mock_place.side_effect = DhanBrokerError("Insufficient funds")
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    assert order.status == "REJECTED"
    assert order.rejection_reason == "Insufficient funds"
    assert order.broker_order_id is None


def test_refresh_updates_status(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)

    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    with patch.object(
        order_service.broker, "get_order_status", return_value={"order_id": "ORD1", "order_status": "TRADED"}
    ):
        refreshed = order_service.refresh_order_status(db_session, test_user, order.id)

    assert refreshed.status == "TRADED"


def test_refresh_on_rejected_order_is_a_noop(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", side_effect=DhanBrokerError("no funds")
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    refreshed = order_service.refresh_order_status(db_session, test_user, order.id)
    assert refreshed.status == "REJECTED"  # unchanged, no broker call attempted


def test_list_trades_filters_to_terminal_statuses(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True):
        with patch.object(order_service.broker, "place_order", return_value={"order_id": "A", "order_status": "TRADED"}):
            order_service.place_buy_order(db_session, test_user, "TCS", 5, "MARKET")
        with patch.object(order_service.broker, "place_order", return_value={"order_id": "B", "order_status": "PENDING"}):
            order_service.place_buy_order(db_session, test_user, "TCS", 5, "MARKET")

    trades = order_service.list_trades(db_session, test_user)
    assert len(trades) == 1
    assert trades[0].broker_order_id == "A"


def test_orders_api_requires_auth(client):
    assert client.get("/orders").status_code == 401
    assert client.post("/orders/preview", json={"symbol": "TCS", "side": "BUY", "quantity": 1, "order_type": "MARKET"}).status_code == 401


# ---------- Order cancellation ----------


def test_cancel_pending_order_succeeds(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    with patch.object(
        order_service.broker, "cancel_order", return_value={"order_id": "ORD1", "order_status": "CANCELLED"}
    ) as mock_cancel:
        cancelled = order_service.cancel_order(db_session, test_user, order.id)

    assert cancelled.status == "CANCELLED"
    call_args = mock_cancel.call_args
    assert call_args.args == ("FAKE_ACCESS_TOKEN", "DHAN_TEST_999", "ORD1")


def test_cancel_order_that_never_reached_broker_rejected(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", side_effect=DhanBrokerError("no funds")
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    try:
        order_service.cancel_order(db_session, test_user, order.id)
        assert False, "should have raised"
    except order_service.OrderValidationError as exc:
        assert "nothing to cancel" in str(exc).lower()


def test_cancel_already_traded_order_rejected(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "TRADED"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    try:
        order_service.cancel_order(db_session, test_user, order.id)
        assert False, "should have raised"
    except order_service.OrderValidationError as exc:
        assert "already" in str(exc).lower()


def test_cancel_unknown_order_404(db_session, test_user):
    _connected_broker(db_session, test_user)
    try:
        order_service.cancel_order(db_session, test_user, 99999)
        assert False, "should have raised"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_cancel_another_users_order_blocked(db_session, test_user, seeded_stock):
    """IDOR check, same pattern as the rest of the codebase."""
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    from app.models.user import User
    from app.utils.security import hash_password

    other_user = User(
        email="otherorderuser@example.com",
        full_name="Other",
        hashed_password=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    try:
        order_service.cancel_order(db_session, other_user, order.id)
        assert False, "should have raised"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_cancel_order_api_requires_auth(client):
    assert client.post("/orders/1/cancel").status_code == 401


# ---------- Order modification ----------


def test_modify_pending_limit_order_succeeds(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "LIMIT", 3500.0)

    with patch.object(
        order_service.broker, "modify_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ) as mock_modify:
        modified = order_service.modify_order(db_session, test_user, order.id, quantity=20, price=3600.0)

    assert modified.quantity == 20
    assert modified.price == 3600.0
    call_args = mock_modify.call_args
    assert call_args.args == ("FAKE_ACCESS_TOKEN", "DHAN_TEST_999", "ORD1", "LIMIT", 20, 3600.0)


def test_modify_order_partial_fields_keeps_the_other(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "LIMIT", 3500.0)

    with patch.object(order_service.broker, "modify_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}):
        modified = order_service.modify_order(db_session, test_user, order.id, quantity=None, price=3700.0)

    assert modified.quantity == 10  # unchanged
    assert modified.price == 3700.0


def test_modify_order_requires_at_least_one_field(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "LIMIT", 3500.0)

    try:
        order_service.modify_order(db_session, test_user, order.id, quantity=None, price=None)
        assert False, "should have raised"
    except order_service.OrderValidationError as exc:
        assert "at least" in str(exc).lower()


def test_modify_market_order_rejected(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "MARKET")

    try:
        order_service.modify_order(db_session, test_user, order.id, quantity=20, price=None)
        assert False, "should have raised"
    except order_service.OrderValidationError as exc:
        assert "limit" in str(exc).lower()


def test_modify_already_traded_order_rejected(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "TRADED"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "LIMIT", 3500.0)

    try:
        order_service.modify_order(db_session, test_user, order.id, quantity=20, price=None)
        assert False, "should have raised"
    except order_service.OrderValidationError as exc:
        assert "already" in str(exc).lower()


def test_modify_unknown_order_404(db_session, test_user):
    _connected_broker(db_session, test_user)
    try:
        order_service.modify_order(db_session, test_user, 99999, quantity=20, price=None)
        assert False, "should have raised"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_modify_another_users_order_blocked(db_session, test_user, seeded_stock):
    """IDOR check, same pattern as the rest of the codebase."""
    _connected_broker(db_session, test_user)
    with patch("app.services.order_service.is_market_open", return_value=True), patch.object(
        order_service.broker, "place_order", return_value={"order_id": "ORD1", "order_status": "PENDING"}
    ):
        order = order_service.place_buy_order(db_session, test_user, "TCS", 10, "LIMIT", 3500.0)

    from app.models.user import User
    from app.utils.security import hash_password

    other_user = User(
        email="othermodifyuser@example.com",
        full_name="Other",
        hashed_password=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    try:
        order_service.modify_order(db_session, other_user, order.id, quantity=20, price=None)
        assert False, "should have raised"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_modify_order_api_requires_auth(client):
    assert client.post("/orders/1/modify", json={"quantity": 5}).status_code == 401


# ---------- Order preview: real funds/holdings check ----------


def test_preview_without_connected_broker_reports_not_connected(db_session, test_user, seeded_stock):
    preview = order_service.preview_order(db_session, test_user, "TCS", "BUY", 10, "MARKET", None)
    assert preview["broker_check_status"] == "not_connected"
    assert preview["available_balance"] is None
    assert preview["sufficient"] is None


def test_preview_buy_checks_real_funds(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch.object(order_service.broker, "get_fund_limits", return_value={"withdrawable_balance": 1000.0}):
        preview = order_service.preview_order(db_session, test_user, "TCS", "BUY", 10, "LIMIT", 50.0)

    assert preview["broker_check_status"] == "ok"
    assert preview["available_balance"] == 1000.0
    assert preview["sufficient"] is True  # 10 * 50 = 500 <= 1000


def test_preview_buy_flags_insufficient_funds(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch.object(order_service.broker, "get_fund_limits", return_value={"withdrawable_balance": 100.0}):
        preview = order_service.preview_order(db_session, test_user, "TCS", "BUY", 10, "LIMIT", 50.0)

    assert preview["sufficient"] is False  # 500 > 100


def test_preview_sell_checks_real_holdings(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch.object(
        order_service.broker,
        "get_holdings",
        return_value=[{"trading_symbol": "TCS", "available_qty": 5}],
    ):
        preview = order_service.preview_order(db_session, test_user, "TCS", "SELL", 10, "MARKET", None)

    assert preview["broker_check_status"] == "ok"
    assert preview["available_quantity"] == 5
    assert preview["sufficient"] is False  # trying to sell 10, only 5 available


def test_preview_broker_call_failure_reported_honestly(db_session, test_user, seeded_stock):
    _connected_broker(db_session, test_user)
    with patch.object(order_service.broker, "get_fund_limits", side_effect=DhanBrokerError("timeout")):
        preview = order_service.preview_order(db_session, test_user, "TCS", "BUY", 10, "MARKET", None)

    assert preview["broker_check_status"] == "unavailable"
    assert preview["available_balance"] is None
