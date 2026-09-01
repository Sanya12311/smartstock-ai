"""
HTML page routes for the frontend, all under /app/* to avoid colliding with
the JSON API's bare top-level paths (/portfolio, /stocks, /orders, etc. are
already taken by app/api/*.py). Only /login and /register stay top-level,
as public pages outside the authenticated app.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="frontend/templates")

router = APIRouter(prefix="/app", tags=["Pages"])


@router.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"active_page": "dashboard"})


@router.get("/portfolio")
def portfolio_page(request: Request):
    return templates.TemplateResponse(request, "portfolio.html", {"active_page": "portfolio"})


@router.get("/stocks/{symbol}")
def stock_detail_page(request: Request, symbol: str):
    return templates.TemplateResponse(
        request, "stock_detail.html", {"active_page": "stock_analysis", "symbol": symbol.upper()}
    )


@router.get("/orders")
def orders_page(request: Request):
    return templates.TemplateResponse(request, "orders.html", {"active_page": "orders"})


@router.get("/trade-history")
def trade_history_page(request: Request):
    return templates.TemplateResponse(request, "trade_history.html", {"active_page": "trade_history"})


@router.get("/alerts")
def alerts_page(request: Request):
    return templates.TemplateResponse(request, "alerts.html", {"active_page": "alerts"})


@router.get("/paper-trading")
def paper_trading_page(request: Request):
    return templates.TemplateResponse(request, "paper_trading.html", {"active_page": "paper_trading"})


@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {"active_page": "chat"})


@router.get("/news")
def news_page(request: Request):
    return templates.TemplateResponse(request, "news.html", {"active_page": "news"})


@router.get("/broker")
def broker_page(request: Request):
    return templates.TemplateResponse(request, "broker.html", {"active_page": "broker"})


@router.get("/settings")
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"active_page": "settings"})
