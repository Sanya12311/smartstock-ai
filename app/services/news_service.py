"""
Fetches real news headlines from Google News' public RSS search feed and
classifies sentiment with the keyword lexicon in app/analysis/sentiment.py.
No article content or sentiment is invented — if the feed returns nothing,
we return an empty list, not fabricated news.

Note: Google News RSS is a public feed, not a versioned/documented API
contract, so its exact XML shape could change without notice. If parsing
starts failing, that's the first place to check.
"""

import logging
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional
from xml.etree import ElementTree

import requests

from app.analysis.sentiment import classify_sentiment
from app.models.stock import Stock

logger = logging.getLogger(__name__)

RSS_BASE_URL = "https://news.google.com/rss/search"
REQUEST_TIMEOUT_SECONDS = 6


class NewsFetchError(Exception):
    """Raised when the news feed cannot be retrieved or parsed."""


def _build_query(stock: Stock) -> str:
    return f"{stock.symbol} {stock.name} share price"


def _clean_title(title: str, source: str) -> str:
    suffix = f" - {source}"
    if title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def _parse_pubdate(pubdate_text: Optional[str]) -> Optional[str]:
    if not pubdate_text:
        return None
    try:
        dt = parsedate_to_datetime(pubdate_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def fetch_news_for_stock(stock: Stock, limit: int = 10) -> List[dict]:
    params = {"q": _build_query(stock), "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}

    try:
        response = requests.get(RSS_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise NewsFetchError(f"Failed to fetch news feed: {exc}") from exc

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        raise NewsFetchError(f"Failed to parse news feed: {exc}") from exc

    items = root.findall("./channel/item")[:limit]
    articles = []
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el = item.find("source")

        source_name = source_el.text if source_el is not None and source_el.text else "Unknown"
        raw_title = title_el.text if title_el is not None and title_el.text else ""
        headline = _clean_title(raw_title, source_name)
        sentiment_result = classify_sentiment(headline)

        articles.append(
            {
                "headline": headline,
                "source": source_name,
                "published_at": _parse_pubdate(pubdate_el.text if pubdate_el is not None else None),
                "url": link_el.text if link_el is not None else "",
                "sentiment": sentiment_result["sentiment"],
                "matched_keywords": sentiment_result["matched_keywords"],
            }
        )

    return articles


def _summarize_sentiment(articles: List[dict]) -> dict:
    positive = sum(1 for a in articles if a["sentiment"] == "POSITIVE")
    negative = sum(1 for a in articles if a["sentiment"] == "NEGATIVE")
    neutral = sum(1 for a in articles if a["sentiment"] == "NEUTRAL")

    if not articles:
        overall = "NEUTRAL"
    elif positive > negative:
        overall = "POSITIVE"
    elif negative > positive:
        overall = "NEGATIVE"
    else:
        overall = "NEUTRAL"

    return {"positive": positive, "neutral": neutral, "negative": negative, "overall": overall}


def build_stock_news(stock: Stock, limit: int = 10) -> dict:
    articles = fetch_news_for_stock(stock, limit)
    return {
        "symbol": stock.symbol,
        "articles": articles,
        "sentiment_summary": _summarize_sentiment(articles),
    }
