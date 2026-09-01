"""
Pure, deterministic technical indicator calculations over a daily OHLCV
series. Every value here is a standard, well-known formula computed
directly from the input data — nothing is randomly generated or guessed.
"""

from statistics import pstdev
from typing import List, Optional


def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: List[float], period: int) -> List[float]:
    """Full EMA series, seeded with an SMA of the first `period` values."""
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    ema_values = [sum(values[:period]) / period]
    for price in values[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def ema(values: List[float], period: int) -> Optional[float]:
    series = ema_series(values, period)
    return series[-1] if series else None


def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[dict]:
    if len(closes) < slow + signal:
        return None

    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    offset = len(fast_ema) - len(slow_ema)
    macd_line_series = [f - s for f, s in zip(fast_ema[offset:], slow_ema)]

    signal_series = ema_series(macd_line_series, signal)
    if not signal_series:
        return None

    macd_line = macd_line_series[-1]
    signal_line = signal_series[-1]
    return {
        "macd_line": round(macd_line, 2),
        "signal_line": round(signal_line, 2),
        "histogram": round(macd_line - signal_line, 2),
    }


def volatility_percent(closes: List[float], period: int = 20) -> Optional[float]:
    """Standard deviation of daily returns over the window, as a percent."""
    if len(closes) < period + 1:
        return None
    window = closes[-(period + 1):]
    returns = [(window[i] - window[i - 1]) / window[i - 1] for i in range(1, len(window))]
    return round(pstdev(returns) * 100, 2)


def support_resistance(highs: List[float], lows: List[float], period: int = 20) -> Optional[dict]:
    if len(highs) < period or len(lows) < period:
        return None
    return {
        "support": round(min(lows[-period:]), 2),
        "resistance": round(max(highs[-period:]), 2),
    }


def volume_ratio(volumes: List[int], period: int = 20) -> Optional[dict]:
    if len(volumes) < period:
        return None
    avg_volume = sum(volumes[-period:]) / period
    latest_volume = volumes[-1]
    ratio = latest_volume / avg_volume if avg_volume else None
    return {
        "latest_volume": latest_volume,
        "avg_volume_20d": round(avg_volume, 0),
        "ratio": round(ratio, 2) if ratio is not None else None,
    }


def price_change_percent(closes: List[float], period: int = 10) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    start = closes[-(period + 1)]
    end = closes[-1]
    if start == 0:
        return None
    return round(((end - start) / start) * 100, 2)
