"""
Thin wrapper around DhanHQ's Market Quote REST API (v2).

Reference (verified against official docs and the DhanHQ-py SDK source,
August 2026):
  https://dhanhq.co/docs/v2/market-quote/
  https://dhanhq.co/docs/v2/authentication/
  https://github.com/dhan-oss/DhanHQ-py

Dhan does not accept plain trading symbols ("TCS") in this API — it needs
their internal numeric Security ID per instrument, grouped by exchange
segment (e.g. "NSE_EQ"). Those ids come from Dhan's public scrip master
CSV and are stored on the Stock model, not looked up here.
"""

import requests

from app.config import settings

DHAN_BASE_URL = "https://api.dhan.co/v2"
REQUEST_TIMEOUT_SECONDS = 5


class DhanAPIError(Exception):
    """Raised whenever live market data cannot be retrieved from Dhan."""


def _headers() -> dict:
    if not settings.DHAN_CLIENT_ID or not settings.DHAN_ACCESS_TOKEN:
        raise DhanAPIError(
            "Dhan API credentials are not configured. Set DHAN_CLIENT_ID and "
            "DHAN_ACCESS_TOKEN in .env (see Phase 4 setup instructions)."
        )
    return {
        "access-token": settings.DHAN_ACCESS_TOKEN,
        "client-id": settings.DHAN_CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_full_quote(exchange_segment: str, security_id: str) -> dict:
    """Fetch full quote data (LTP, OHLC, volume, net change) for one instrument."""
    url = f"{DHAN_BASE_URL}/marketfeed/quote"
    payload = {exchange_segment: [int(security_id)]}

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise DhanAPIError(f"Dhan API request failed: {exc}") from exc

    body = response.json()
    if body.get("status") != "success":
        raise DhanAPIError(f"Dhan API returned an error: {body}")

    try:
        return body["data"][exchange_segment][str(security_id)]
    except KeyError as exc:
        raise DhanAPIError(f"Unexpected Dhan API response shape: {body}") from exc


def get_historical_daily(
    exchange_segment: str, security_id: str, from_date: str, to_date: str
) -> dict:
    """Fetch daily OHLCV candles. Verified against the DhanHQ-py SDK source
    (dhanhq/_historical_data.py) — the `client-id` header is required here
    too, even though the public docs page for this endpoint omits it."""
    url = f"{DHAN_BASE_URL}/charts/historical"
    payload = {
        "securityId": security_id,
        "exchangeSegment": exchange_segment,
        "instrument": "EQUITY",
        "expiryCode": 0,
        "oi": False,
        "fromDate": from_date,
        "toDate": to_date,
    }

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise DhanAPIError(f"Dhan API request failed: {exc}") from exc

    body = response.json()
    required_keys = {"open", "high", "low", "close", "volume"}
    if not required_keys.issubset(body.keys()):
        raise DhanAPIError(f"Unexpected Dhan historical data response shape: {body}")
    return body
