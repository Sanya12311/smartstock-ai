"""
Transparent, rule-based stock risk assessment.

Each factor below adds a fixed number of "risk points" (0-100 total) based
on a real, computed value — never randomly generated. Higher = riskier.
"""

from typing import List, Optional, Tuple


def _volatility_risk(volatility_20d_percent: Optional[float]) -> Tuple[int, Optional[str]]:
    if volatility_20d_percent is None:
        return 0, None
    if volatility_20d_percent > 3.5:
        return 40, f"20-day volatility is high at {volatility_20d_percent:.1f}% daily swings."
    if volatility_20d_percent > 2.0:
        return 20, f"20-day volatility is moderate at {volatility_20d_percent:.1f}% daily swings."
    return 0, None


def _rsi_risk(rsi_14: Optional[float]) -> Tuple[int, Optional[str]]:
    if rsi_14 is None:
        return 0, None
    if rsi_14 >= 75 or rsi_14 <= 25:
        return 20, f"RSI at {rsi_14:.1f} is at an extreme, raising reversal risk."
    if rsi_14 >= 70 or rsi_14 <= 30:
        return 10, f"RSI at {rsi_14:.1f} is near overbought/oversold territory."
    return 0, None


def _momentum_risk(price_change_10d_percent: Optional[float]) -> Tuple[int, Optional[str]]:
    if price_change_10d_percent is None:
        return 0, None
    change = abs(price_change_10d_percent)
    if change > 10:
        return 20, f"Price moved {change:.1f}% in 10 days — a large swing raises correction risk."
    if change > 6:
        return 10, f"Price moved {change:.1f}% in 10 days — a moderately large recent swing."
    return 0, None


def _technical_weakness_risk(technical_score: int) -> Tuple[int, Optional[str]]:
    if technical_score < 40:
        return 20, f"Technical score of {technical_score}/100 indicates a weak setup."
    if technical_score < 60:
        return 10, f"Technical score of {technical_score}/100 is only moderate."
    return 0, None


def assess_stock_risk(
    volatility_20d_percent: Optional[float],
    rsi_14: Optional[float],
    price_change_10d_percent: Optional[float],
    technical_score: int,
) -> dict:
    reasons: List[str] = []
    total = 0

    for points, reason in [
        _volatility_risk(volatility_20d_percent),
        _rsi_risk(rsi_14),
        _momentum_risk(price_change_10d_percent),
        _technical_weakness_risk(technical_score),
    ]:
        total += points
        if reason:
            reasons.append(reason)

    total = min(total, 100)

    if total >= 60:
        level = "HIGH"
    elif total >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not reasons:
        reasons.append(
            "No significant volatility, momentum, RSI, or technical-weakness risk factors detected."
        )

    return {"risk_score": total, "risk_level": level, "reasons": reasons}
