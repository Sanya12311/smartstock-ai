"""
Fundamental analysis (P/E, ROE, EPS, revenue growth, etc.) — section 8 of
the master spec.

RESEARCHED AND DELIBERATELY NOT IMPLEMENTED with real data (Phase 20):
- DhanHQ's full API index has no fundamentals endpoint at all (Orders,
  Portfolio, Market Quote, Historical Data, Option Chain — no financials).
- yfinance (the common free option with India coverage) was tested
  directly against TCS.NS and found materially inconsistent with real
  market prices — its reported price (~2,370) sat ~37% below TCS's real
  price from an actual news headline the same week, and even below
  yfinance's own reported 52-week high. That's not normal data lag; it's
  unreliable enough that showing P/E or EPS computed from it alongside
  our own live Dhan price would be actively misleading.
- No other reliable, verified, India-covering free source was found.

Per the master spec's own instruction for exactly this situation: "If
data is unavailable: 'Data unavailable'. Never invent financial data."
So every field here is honestly None until a verified provider is
integrated — this is not a placeholder to fill in later by guessing.
"""

from app.models.stock import Stock

NO_SOURCE_NOTE = (
    "No verified fundamental-data provider is integrated yet. DhanHQ's API "
    "has no fundamentals endpoint, and the common free alternative "
    "(yfinance) was tested and found materially inconsistent with real "
    "market prices — showing it here would risk misleading you, so it was "
    "deliberately left out rather than guessed at."
)


def get_fundamental_data(stock: Stock) -> dict:
    return {
        "symbol": stock.symbol,
        "data_available": False,
        "note": NO_SOURCE_NOTE,
        "source": None,
        "as_of": None,
        "pe_ratio": None,
        "forward_pe": None,
        "eps": None,
        "roe": None,
        "debt_to_equity": None,
        "revenue_growth_percent": None,
        "profit_growth_percent": None,
        "dividend_yield_percent": None,
        "market_cap": None,
    }
