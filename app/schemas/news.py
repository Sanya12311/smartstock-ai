from typing import List, Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    headline: str
    source: str
    published_at: Optional[str] = None
    url: str
    sentiment: str
    matched_keywords: List[str]


class SentimentSummary(BaseModel):
    positive: int
    neutral: int
    negative: int
    overall: str


class StockNews(BaseModel):
    symbol: str
    articles: List[NewsItem]
    sentiment_summary: SentimentSummary
