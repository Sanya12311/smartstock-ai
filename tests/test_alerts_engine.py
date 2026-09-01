from datetime import date
from unittest.mock import patch

from app.alerts.engine import evaluate_all_alerts
from app.models.alert import Alert
from app.models.portfolio_holding import PortfolioHolding


def _mock_price(price):
    return patch("app.alerts.engine.stock_service.resolve_current_price", return_value=(price, "live"))


def test_price_above_alert_triggers(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PRICE_ABOVE", threshold=3400)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(3450.0):
        notifications = evaluate_all_alerts(db_session)

    assert len(notifications) == 1
    assert notifications[0]["category"] == "PRICE"
    assert "3,400" in notifications[0]["title"] or "3400" in notifications[0]["title"]


def test_price_below_alert_does_not_trigger_when_price_is_higher(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PRICE_BELOW", threshold=1000)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(3450.0):
        notifications = evaluate_all_alerts(db_session)

    assert notifications == []


def test_cooldown_prevents_immediate_retrigger(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PRICE_ABOVE", threshold=3400)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(3450.0):
        first = evaluate_all_alerts(db_session)
        second = evaluate_all_alerts(db_session)

    assert len(first) == 1
    assert len(second) == 0  # same alert, still within cooldown


def test_profit_alert_uses_actual_holding_buy_price(db_session, test_user, seeded_stock):
    holding = PortfolioHolding(
        user_id=test_user.id, symbol="TCS", quantity=10, buy_price=3000, buy_date=date(2026, 1, 15)
    )
    db_session.add(holding)
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PROFIT_PERCENT", threshold=10)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(3450.0):  # +15% vs buy price of 3000
        notifications = evaluate_all_alerts(db_session)

    assert len(notifications) == 1
    assert notifications[0]["category"] == "PROFIT"


def test_profit_alert_does_not_trigger_below_threshold(db_session, test_user, seeded_stock):
    holding = PortfolioHolding(
        user_id=test_user.id, symbol="TCS", quantity=10, buy_price=3000, buy_date=date(2026, 1, 15)
    )
    db_session.add(holding)
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PROFIT_PERCENT", threshold=20)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(3450.0):  # only +15%, threshold is +20%
        notifications = evaluate_all_alerts(db_session)

    assert notifications == []


def test_rsi_overbought_triggers_with_mocked_analysis(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="RSI_OVERBOUGHT", threshold=70)
    db_session.add(alert)
    db_session.commit()

    fake_analysis = {"indicators": {"rsi_14": 78.0, "macd": {"macd_line": 0, "signal_line": 0, "histogram": 0}}}
    with patch("app.alerts.engine.analysis_service.build_technical_analysis", return_value=fake_analysis):
        notifications = evaluate_all_alerts(db_session)

    assert len(notifications) == 1
    assert notifications[0]["category"] == "TECHNICAL"


def test_macd_cross_does_not_fire_on_first_observation(db_session, test_user, seeded_stock):
    """First time we see MACD state, there's no 'previous' to compare against —
    it must NOT be reported as a crossover."""
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="MACD_CROSS")
    db_session.add(alert)
    db_session.commit()

    fake_analysis = {
        "indicators": {"rsi_14": 50.0, "macd": {"macd_line": -0.5, "signal_line": -0.2, "histogram": -0.3}}
    }
    with patch("app.alerts.engine.analysis_service.build_technical_analysis", return_value=fake_analysis):
        notifications = evaluate_all_alerts(db_session)

    assert notifications == []
    db_session.refresh(alert)
    assert alert.last_state == "bearish"


def test_macd_cross_fires_when_state_actually_flips(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="MACD_CROSS")
    db_session.add(alert)
    db_session.commit()

    bearish = {"indicators": {"rsi_14": 50.0, "macd": {"macd_line": -0.5, "signal_line": -0.2, "histogram": -0.3}}}
    bullish = {"indicators": {"rsi_14": 50.0, "macd": {"macd_line": 0.5, "signal_line": 0.2, "histogram": 0.3}}}

    with patch("app.alerts.engine.analysis_service.build_technical_analysis", return_value=bearish):
        evaluate_all_alerts(db_session)  # establishes initial state, no notification
    with patch("app.alerts.engine.analysis_service.build_technical_analysis", return_value=bullish):
        notifications = evaluate_all_alerts(db_session)

    assert len(notifications) == 1
    assert "bullish" in notifications[0]["message"]


def test_inactive_alert_never_evaluated(db_session, test_user, seeded_stock):
    alert = Alert(user_id=test_user.id, symbol="TCS", alert_type="PRICE_ABOVE", threshold=100, is_active=False)
    db_session.add(alert)
    db_session.commit()

    with _mock_price(999999.0):
        notifications = evaluate_all_alerts(db_session)

    assert notifications == []
