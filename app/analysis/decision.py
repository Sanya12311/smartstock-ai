"""
Transparent decision matrix combining the Technical Score (Phase 7) with the
Risk level (Phase 8). A fixed lookup table, not a model or a guess.
"""

DECISION_TABLE = {
    ("high", "LOW"): "FAVORABLE",
    ("high", "MEDIUM"): "HOLD",
    ("high", "HIGH"): "CAUTION",
    ("mid", "LOW"): "HOLD",
    ("mid", "MEDIUM"): "MONITOR",
    ("mid", "HIGH"): "CAUTION",
    ("low", "LOW"): "MONITOR",
    ("low", "MEDIUM"): "CAUTION",
    ("low", "HIGH"): "HIGH RISK",
}

DISCLAIMER = (
    "This is an automated analysis signal based on technical indicators and risk "
    "factors only. It is not financial advice and does not guarantee future returns."
)


def _technical_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 50:
        return "mid"
    return "low"


def compute_decision(technical_score: int, risk_level: str) -> dict:
    band = _technical_band(technical_score)
    decision = DECISION_TABLE[(band, risk_level)]
    reason = (
        f"Technical score of {technical_score}/100 combined with {risk_level} risk "
        f"maps to a '{decision}' signal."
    )
    return {"decision": decision, "reason": reason, "disclaimer": DISCLAIMER}
