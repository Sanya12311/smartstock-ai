from typing import List, Optional

from pydantic import BaseModel


class MacdData(BaseModel):
    macd_line: float
    signal_line: float
    histogram: float


class VolumeData(BaseModel):
    latest_volume: int
    avg_volume_20d: float
    ratio: Optional[float] = None


class TechnicalIndicators(BaseModel):
    current_price: float
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[MacdData] = None
    volatility_20d_percent: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    volume: Optional[VolumeData] = None
    price_change_10d_percent: Optional[float] = None


class ScoreComponent(BaseModel):
    component: str
    score: int
    max: int
    reason: str


class RiskAssessment(BaseModel):
    risk_score: int
    risk_level: str
    reasons: List[str]


class Decision(BaseModel):
    decision: str
    reason: str
    disclaimer: str


class TechnicalAnalysis(BaseModel):
    symbol: str
    as_of: str
    indicators: TechnicalIndicators
    technical_score: int
    score_breakdown: List[ScoreComponent]
    risk: RiskAssessment
    decision: Decision
