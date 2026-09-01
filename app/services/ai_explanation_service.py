from app.ai.gemini_client import generate_explanation
from app.models.stock import Stock
from app.services import analysis_service, news_service
from app.services.news_service import NewsFetchError

DISCLAIMER = "AI-generated analysis is informational and is not guaranteed financial advice."


def explain_stock(stock: Stock) -> dict:
    """
    Build a structured, verified context from our own analysis engines
    (Phases 7-9) and ask Gemini to explain it in plain language. Gemini
    never sees or invents raw prices/news on its own — only what we hand it.
    """
    analysis = analysis_service.build_technical_analysis(stock)

    try:
        news = news_service.build_stock_news(stock, limit=5)
        news_sentiment = news["sentiment_summary"]["overall"]
    except NewsFetchError:
        news_sentiment = "unavailable"

    context = {
        "symbol": analysis["symbol"],
        "as_of": analysis["as_of"],
        "current_price": analysis["indicators"]["current_price"],
        "rsi_14": analysis["indicators"]["rsi_14"],
        "macd": analysis["indicators"]["macd"],
        "price_change_10d_percent": analysis["indicators"]["price_change_10d_percent"],
        "technical_score": analysis["technical_score"],
        "risk_level": analysis["risk"]["risk_level"],
        "risk_reasons": analysis["risk"]["reasons"],
        "decision": analysis["decision"]["decision"],
        "news_sentiment": news_sentiment,
    }

    explanation_text = generate_explanation(context)

    return {
        "symbol": stock.symbol,
        "context": context,
        "explanation": explanation_text,
        "disclaimer": DISCLAIMER,
    }
