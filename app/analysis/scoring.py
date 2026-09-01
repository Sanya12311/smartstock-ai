"""
Transparent, rule-based Technical Score (0-100).

Five components, 20 points each, each scored from a fixed threshold table
over a real indicator value. The same inputs always produce the same score
and the same plain-English reason — nothing here is random or ML-guessed.
"""

from typing import Optional, Tuple

MAX_COMPONENT_SCORE = 20


def _trend_score(price: float, sma_20: Optional[float], sma_50: Optional[float]) -> Tuple[int, str]:
    if sma_20 is None or sma_50 is None:
        return 10, "Not enough history yet to judge the trend; treated as neutral."
    above_20 = price > sma_20
    rising = sma_20 > sma_50
    if above_20 and rising:
        return 20, f"Price ({price:.2f}) is above both SMA20 ({sma_20:.2f}) and SMA50 ({sma_50:.2f}) — uptrend."
    if above_20 or rising:
        return 12, "Price is above only one of SMA20/SMA50 — mixed trend signal."
    return 0, f"Price ({price:.2f}) is below both SMA20 and SMA50 — downtrend."


def _rsi_score(rsi_value: Optional[float]) -> Tuple[int, str]:
    if rsi_value is None:
        return 10, "Not enough history to compute RSI; treated as neutral."
    if 50 <= rsi_value < 70:
        return 20, f"RSI at {rsi_value:.1f} shows healthy bullish momentum without being overbought."
    if 40 <= rsi_value < 50:
        return 12, f"RSI at {rsi_value:.1f} is neutral."
    if rsi_value >= 70:
        return 8, f"RSI at {rsi_value:.1f} is overbought — risk of a pullback."
    if 30 <= rsi_value < 40:
        return 8, f"RSI at {rsi_value:.1f} shows weakening momentum."
    return 10, f"RSI at {rsi_value:.1f} is oversold — could bounce, but reflects recent weakness."


def _macd_score(macd_data: Optional[dict]) -> Tuple[int, str]:
    if macd_data is None:
        return 10, "Not enough history to compute MACD; treated as neutral."
    macd_line = macd_data["macd_line"]
    signal_line = macd_data["signal_line"]
    histogram = macd_data["histogram"]
    if macd_line > signal_line and histogram > 0:
        return 20, "MACD line is above the signal line with a positive histogram — bullish crossover."
    if macd_line > signal_line:
        return 12, "MACD line is above the signal line but momentum is flattening."
    return 0, "MACD line is below the signal line — bearish."


def _momentum_score(change_percent: Optional[float]) -> Tuple[int, str]:
    if change_percent is None:
        return 10, "Not enough history to compute momentum; treated as neutral."
    if change_percent > 5:
        return 20, f"Price is up {change_percent:.1f}% over the last 10 trading days — strong momentum."
    if change_percent >= 0:
        return 12, f"Price is up {change_percent:.1f}% over the last 10 trading days — mild momentum."
    if change_percent >= -5:
        return 6, f"Price is down {abs(change_percent):.1f}% over the last 10 trading days — mild weakness."
    return 0, f"Price is down {abs(change_percent):.1f}% over the last 10 trading days — strong weakness."


def _volume_score(volume_data: Optional[dict]) -> Tuple[int, str]:
    if volume_data is None or volume_data.get("ratio") is None:
        return 10, "Not enough history to compute volume trend; treated as neutral."
    ratio = volume_data["ratio"]
    if ratio >= 1.5:
        return 20, f"Latest volume is {ratio:.1f}x the 20-day average — strong interest."
    if ratio >= 1.0:
        return 12, f"Latest volume is roughly in line with the 20-day average ({ratio:.1f}x)."
    if ratio >= 0.5:
        return 6, f"Latest volume is below the 20-day average ({ratio:.1f}x) — weak participation."
    return 0, f"Latest volume is well below the 20-day average ({ratio:.1f}x) — very weak participation."


def compute_technical_score(
    price: float,
    sma_20: Optional[float],
    sma_50: Optional[float],
    rsi_value: Optional[float],
    macd_data: Optional[dict],
    change_percent: Optional[float],
    volume_data: Optional[dict],
) -> dict:
    components = [
        ("trend", *_trend_score(price, sma_20, sma_50)),
        ("rsi", *_rsi_score(rsi_value)),
        ("macd", *_macd_score(macd_data)),
        ("momentum", *_momentum_score(change_percent)),
        ("volume", *_volume_score(volume_data)),
    ]

    total = sum(score for _, score, _ in components)
    breakdown = [
        {"component": name, "score": score, "max": MAX_COMPONENT_SCORE, "reason": reason}
        for name, score, reason in components
    ]

    return {"technical_score": total, "score_breakdown": breakdown}
