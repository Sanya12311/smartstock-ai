def test_fundamentals_honestly_unavailable(client, auth_headers, seeded_stock):
    """No verified fundamental-data provider is integrated (Phase 20 finding:
    DhanHQ has no fundamentals endpoint, yfinance was tested and found
    materially inconsistent with real prices). Every field must be None,
    never a guessed/fabricated number, and the endpoint must say so clearly."""
    response = client.get("/stocks/TCS/fundamentals", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["symbol"] == "TCS"
    assert body["data_available"] is False
    assert len(body["note"]) > 0

    numeric_fields = [
        "pe_ratio", "forward_pe", "eps", "roe", "debt_to_equity",
        "revenue_growth_percent", "profit_growth_percent",
        "dividend_yield_percent", "market_cap",
    ]
    for field in numeric_fields:
        assert body[field] is None, f"{field} should be None, not a guessed value"


def test_fundamentals_unknown_symbol_404(client, auth_headers):
    response = client.get("/stocks/FAKESYM/fundamentals", headers=auth_headers)
    assert response.status_code == 404


def test_fundamentals_requires_auth(client):
    assert client.get("/stocks/TCS/fundamentals").status_code == 401
