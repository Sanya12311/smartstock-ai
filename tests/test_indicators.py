import random

import pytest

from app.analysis import indicators


def _synthetic_prices(n=100, seed=42):
    random.seed(seed)
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(round(closes[-1] * (1 + random.uniform(-0.02, 0.025)), 2))
    return closes


def test_sma_known_values():
    closes = [10, 20, 30, 40, 50]
    assert indicators.sma(closes, 5) == 30
    assert indicators.sma(closes, 3) == 40  # avg of 30, 40, 50


def test_sma_insufficient_data_returns_none():
    assert indicators.sma([1, 2], 5) is None


def test_sma_matches_pandas_reference():
    pd = pytest.importorskip("pandas")
    closes = _synthetic_prices()
    expected = pd.Series(closes).rolling(20).mean().iloc[-1]
    assert indicators.sma(closes, 20) == pytest.approx(expected)


def test_ema_flat_series_equals_the_flat_value():
    closes = [10.0] * 20
    assert indicators.ema(closes, 12) == pytest.approx(10.0)


def test_ema_matches_pandas_reference():
    pd = pytest.importorskip("pandas")
    closes = _synthetic_prices()
    expected = pd.Series(closes).ewm(span=12, adjust=False).mean().iloc[-1]
    assert indicators.ema(closes, 12) == pytest.approx(expected)


def test_rsi_all_gains_is_100():
    closes = list(range(1, 20))  # strictly increasing, no losses at all
    assert indicators.rsi(closes, 14) == 100.0


def test_rsi_all_losses_is_0():
    closes = list(range(20, 1, -1))  # strictly decreasing, no gains at all
    assert indicators.rsi(closes, 14) == 0.0


def test_rsi_bounded_between_0_and_100():
    closes = _synthetic_prices()
    rsi = indicators.rsi(closes, 14)
    assert 0 <= rsi <= 100


def test_rsi_insufficient_data_returns_none():
    assert indicators.rsi([1, 2, 3], 14) is None


def test_macd_insufficient_data_returns_none():
    assert indicators.macd([1, 2, 3]) is None


def test_macd_returns_all_three_components():
    closes = _synthetic_prices()
    result = indicators.macd(closes)
    assert set(result.keys()) == {"macd_line", "signal_line", "histogram"}
    assert result["histogram"] == pytest.approx(result["macd_line"] - result["signal_line"])


def test_volatility_zero_for_constant_price():
    closes = [100.0] * 25
    assert indicators.volatility_percent(closes, 20) == 0.0


def test_volatility_positive_for_varying_prices():
    closes = _synthetic_prices()
    vol = indicators.volatility_percent(closes, 20)
    assert vol > 0


def test_support_resistance_picks_correct_extremes():
    highs = [10, 12, 15, 11, 9] * 5
    lows = [8, 9, 7, 6, 5] * 5
    result = indicators.support_resistance(highs, lows, 20)
    assert result["resistance"] == 15
    assert result["support"] == 5


def test_volume_ratio_calculation():
    volumes = [100] * 19 + [300]
    result = indicators.volume_ratio(volumes, 20)
    avg = (100 * 19 + 300) / 20
    assert result["ratio"] == pytest.approx(300 / avg, rel=1e-2)
    assert result["latest_volume"] == 300


def test_price_change_percent_known_value():
    closes = [100] * 10 + [110]
    change = indicators.price_change_percent(closes, 10)
    assert change == pytest.approx(10.0)


def test_price_change_percent_negative():
    closes = [100] * 10 + [90]
    change = indicators.price_change_percent(closes, 10)
    assert change == pytest.approx(-10.0)
