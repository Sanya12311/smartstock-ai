from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.ai.gemini_client import GeminiError
from app.schemas.ai import StockExplanation
from app.schemas.analysis import TechnicalAnalysis
from app.schemas.fundamentals import FundamentalData
from app.schemas.news import StockNews
from app.schemas.stock import StockOut, StockQuote
from app.services import (
    ai_explanation_service,
    analysis_service,
    fundamental_service,
    news_service,
    stock_service,
)
from app.services.dhan_client import DhanAPIError
from app.services.news_service import NewsFetchError

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/search", response_model=list[StockOut])
def search_stocks(
    q: str = Query(min_length=1, description="Symbol or company name, e.g. 'TCS'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return stock_service.search_stocks(db, q)


@router.get("/{symbol}", response_model=StockQuote)
def get_stock_quote(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock '{symbol}' not found"
        )

    try:
        quote = stock_service.build_stock_quote(stock)
    except DhanAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable: {exc}",
        )

    return quote


@router.get("/{symbol}/analysis", response_model=TechnicalAnalysis)
def get_stock_analysis(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock '{symbol}' not found"
        )

    try:
        return analysis_service.build_technical_analysis(stock)
    except DhanAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Technical analysis unavailable: {exc}",
        )


@router.get("/{symbol}/news", response_model=StockNews)
def get_stock_news(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock '{symbol}' not found"
        )

    try:
        return news_service.build_stock_news(stock)
    except NewsFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"News unavailable: {exc}"
        )


@router.get("/{symbol}/fundamentals", response_model=FundamentalData)
def get_stock_fundamentals(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Always returns 200 with data_available=False right now — this isn't a
    transient outage (503 would imply "retry later, it might work"), it's
    a documented, permanent state until a verified data provider is
    integrated. See app/services/fundamental_service.py for why.
    """
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock '{symbol}' not found"
        )
    return fundamental_service.get_fundamental_data(stock)


@router.get("/{symbol}/explain", response_model=StockExplanation)
def get_stock_explanation(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock '{symbol}' not found"
        )

    try:
        return ai_explanation_service.explain_stock(stock)
    except DhanAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Technical analysis unavailable: {exc}",
        )
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI explanation unavailable: {exc}",
        )
