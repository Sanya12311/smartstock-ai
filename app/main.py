import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.alerts import scheduler as alert_scheduler
from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.broker import router as broker_router
from app.api.chat import router as chat_router
from app.api.market import router as market_router
from app.api.notifications import router as notifications_router
from app.api.orders import router as orders_router
from app.api.paper_trading import router as paper_trading_router
from app.api.portfolio import router as portfolio_router
from app.api.stocks import router as stocks_router
from app.api.trades import router as trades_router
from app.api.watchlist import router as watchlist_router
from app.config import settings
from app.database import check_db_connection
from app.logging_config import configure_logging
from app.pages import router as pages_router
from app.services import dhan_feed
from app.services import order_scheduler
from app.utils.security import decode_access_token

configure_logging()
access_logger = logging.getLogger("smartstock.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    dhan_feed.start()
    alert_scheduler.start()
    order_scheduler.start()
    yield
    order_scheduler.stop()
    alert_scheduler.stop()
    dhan_feed.stop()


app = FastAPI(
    title="SmartStock AI",
    description="AI-Powered Stock Advisor, Portfolio Manager & Trading Platform (educational/decision-support tool, not financial advice)",
    version="0.1.0",
    lifespan=lifespan,
)

def _identify_caller(request: Request) -> str:
    """Best-effort user identification for logging only — never used for
    authorization. A failed/missing token just logs as anonymous."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return "anonymous"
    payload = decode_access_token(auth_header[7:])
    if payload is None:
        return "anonymous"
    return payload.get("sub", "anonymous")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    # Deliberately logging only method/path/status/duration/user — never
    # headers or the request body, which is where passwords/tokens live.
    access_logger.info(
        "%s %s -> %s (%sms) user=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        _identify_caller(request),
    )
    return response


app.include_router(auth_router)
app.include_router(stocks_router)
app.include_router(market_router)
app.include_router(portfolio_router)
app.include_router(chat_router)
app.include_router(alerts_router)
app.include_router(notifications_router)
app.include_router(paper_trading_router)
app.include_router(broker_router)
app.include_router(orders_router)
app.include_router(trades_router)
app.include_router(watchlist_router)
app.include_router(pages_router)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")


@app.get("/")
def root():
    return RedirectResponse(url="/login")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/db")
def health_db():
    try:
        check_db_connection()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")
    return {"status": "healthy", "database": settings.DB_NAME}
