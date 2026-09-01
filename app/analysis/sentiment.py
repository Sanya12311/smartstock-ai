"""
Simple, transparent keyword-based sentiment classifier for financial
headlines. Not machine-learned and not random — a fixed lexicon of
positive/negative financial terms. Every classification lists which
keywords triggered it, so the result is always explainable.

This is intentionally simple; a later phase can layer Gemini's richer
natural-language read on top of these same real headlines, but this
rule-based layer works without any AI API and never fabricates a
headline's content or meaning.
"""

from typing import List

POSITIVE_KEYWORDS = [
    "profit", "profits", "growth", "surge", "surges", "rally", "rallies",
    "gain", "gains", "upgrade", "upgraded", "beat", "beats", "record high",
    "outperform", "bullish", "expansion", "buyback", "wins", "win", "deal",
    "partnership", "acquire", "acquisition", "upbeat", "soar", "soars",
    "jump", "jumps", "boost", "rises", "rise", "rising",
]

NEGATIVE_KEYWORDS = [
    "loss", "losses", "decline", "declines", "plunge", "plunges",
    "downgrade", "downgraded", "miss", "misses", "fraud", "lawsuit",
    "probe", "investigation", "layoff", "layoffs", "cut", "cuts", "weak",
    "bearish", "slump", "slumps", "fall", "falls", "falling", "drop",
    "drops", "crash", "resigns", "resign", "scandal", "penalty", "fine",
    "default", "bankruptcy", "warns", "warning",
]


def classify_sentiment(text: str) -> dict:
    lowered = text.lower()
    matched_positive: List[str] = [kw for kw in POSITIVE_KEYWORDS if kw in lowered]
    matched_negative: List[str] = [kw for kw in NEGATIVE_KEYWORDS if kw in lowered]

    if len(matched_positive) > len(matched_negative):
        sentiment = "POSITIVE"
    elif len(matched_negative) > len(matched_positive):
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    return {"sentiment": sentiment, "matched_keywords": matched_positive + matched_negative}
