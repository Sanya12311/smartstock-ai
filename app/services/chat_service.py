import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai.gemini_client import generate_explanation
from app.models.chat import ChatMessage, ChatSession
from app.models.stock import Stock
from app.models.user import User
from app.services import analysis_service, news_service, portfolio_service
from app.services.dhan_client import DhanAPIError
from app.services.news_service import NewsFetchError

DISCLAIMER = "AI-generated analysis is informational and is not guaranteed financial advice."
HISTORY_LIMIT = 10


def get_or_create_session(db: Session, user: User, session_id: Optional[int]) -> ChatSession:
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
            .first()
        )
        if session is None:
            raise ValueError(f"Chat session {session_id} not found")
        return session

    session = ChatSession(user_id=user.id, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _detect_mentioned_stock(db: Session, message: str) -> Optional[Stock]:
    """Look for a known stock symbol appearing as a whole word in the message."""
    words = set(re.findall(r"[A-Za-z]+", message.upper()))
    if not words:
        return None
    return db.query(Stock).filter(Stock.symbol.in_(words)).first()


def _build_context(db: Session, user: User, message: str, history: List[ChatMessage]) -> dict:
    context: dict = {
        "recent_conversation": [{"role": m.role, "content": m.content} for m in history],
    }

    try:
        context["portfolio_summary"] = portfolio_service.get_portfolio_summary(db, user)
    except Exception:
        context["portfolio_summary"] = "unavailable"

    stock = _detect_mentioned_stock(db, message)
    if stock is not None:
        stock_context: dict = {"symbol": stock.symbol, "name": stock.name}

        try:
            analysis = analysis_service.build_technical_analysis(stock)
            stock_context["technical_analysis"] = {
                "technical_score": analysis["technical_score"],
                "risk": analysis["risk"],
                "decision": analysis["decision"],
                "indicators": analysis["indicators"],
            }
        except DhanAPIError as exc:
            stock_context["technical_analysis"] = f"unavailable: {exc}"

        try:
            news = news_service.build_stock_news(stock, limit=5)
            stock_context["news_sentiment"] = news["sentiment_summary"]
        except NewsFetchError as exc:
            stock_context["news_sentiment"] = f"unavailable: {exc}"

        context["mentioned_stock"] = stock_context

    return context


def send_message(db: Session, user: User, session_id: Optional[int], message: str) -> dict:
    session = get_or_create_session(db, user, session_id)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    history.reverse()

    user_message = ChatMessage(session_id=session.id, role="user", content=message)
    db.add(user_message)
    db.commit()

    if session.title == "New chat":
        session.title = message[:50]
        db.commit()

    context = _build_context(db, user, message, history)
    reply_text = generate_explanation(context, user_question=message)

    assistant_message = ChatMessage(session_id=session.id, role="assistant", content=reply_text)
    db.add(assistant_message)
    db.commit()

    return {"session_id": session.id, "reply": reply_text, "disclaimer": DISCLAIMER}


def list_sessions(db: Session, user: User) -> List[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


def get_session_messages(db: Session, user: User, session_id: int) -> List[ChatMessage]:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise ValueError(f"Chat session {session_id} not found")

    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
