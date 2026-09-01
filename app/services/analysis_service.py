from datetime import date, timedelta

from app.analysis import decision, indicators, risk, scoring
from app.models.stock import Stock
from app.services.dhan_client import DhanAPIError, get_historical_daily

MIN_REQUIRED_BARS = 60
HISTORY_LOOKBACK_DAYS = 180  # calendar days; comfortably yields 60+ trading days


def build_technical_analysis(stock: Stock) -> dict:
    to_date = date.today()
    from_date = to_date - timedelta(days=HISTORY_LOOKBACK_DAYS)

    raw = get_historical_daily(
        stock.exchange_segment, stock.security_id, from_date.isoformat(), to_date.isoformat()
    )

    closes = raw.get("close", [])
    highs = raw.get("high", [])
    lows = raw.get("low", [])
    volumes = raw.get("volume", [])

    if len(closes) < MIN_REQUIRED_BARS:
        raise DhanAPIError(
            f"Only {len(closes)} daily bars available; need at least {MIN_REQUIRED_BARS} "
            "for reliable indicators."
        )

    current_price = closes[-1]
    sma_20 = indicators.sma(closes, 20)
    sma_50 = indicators.sma(closes, 50)
    ema_12 = indicators.ema(closes, 12)
    ema_26 = indicators.ema(closes, 26)
    rsi_14 = indicators.rsi(closes, 14)
    macd_data = indicators.macd(closes)
    volatility = indicators.volatility_percent(closes, 20)
    sr = indicators.support_resistance(highs, lows, 20)
    vol_data = indicators.volume_ratio(volumes, 20)
    change_10d = indicators.price_change_percent(closes, 10)

    score_result = scoring.compute_technical_score(
        price=current_price,
        sma_20=sma_20,
        sma_50=sma_50,
        rsi_value=rsi_14,
        macd_data=macd_data,
        change_percent=change_10d,
        volume_data=vol_data,
    )

    risk_result = risk.assess_stock_risk(
        volatility_20d_percent=volatility,
        rsi_14=rsi_14,
        price_change_10d_percent=change_10d,
        technical_score=score_result["technical_score"],
    )

    decision_result = decision.compute_decision(
        technical_score=score_result["technical_score"],
        risk_level=risk_result["risk_level"],
    )

    return {
        "symbol": stock.symbol,
        "as_of": to_date.isoformat(),
        "indicators": {
            "current_price": round(current_price, 2),
            "sma_20": round(sma_20, 2) if sma_20 is not None else None,
            "sma_50": round(sma_50, 2) if sma_50 is not None else None,
            "ema_12": round(ema_12, 2) if ema_12 is not None else None,
            "ema_26": round(ema_26, 2) if ema_26 is not None else None,
            "rsi_14": round(rsi_14, 2) if rsi_14 is not None else None,
            "macd": macd_data,
            "volatility_20d_percent": volatility,
            "support": sr["support"] if sr else None,
            "resistance": sr["resistance"] if sr else None,
            "volume": vol_data,
            "price_change_10d_percent": change_10d,
        },
        "technical_score": score_result["technical_score"],
        "score_breakdown": score_result["score_breakdown"],
        "risk": risk_result,
        "decision": decision_result,
    }
