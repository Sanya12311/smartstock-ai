from app.analysis import decision, risk, scoring


class TestTechnicalScore:
    def test_strong_uptrend_scores_high(self):
        result = scoring.compute_technical_score(
            price=114.0,
            sma_20=110.0,
            sma_50=107.0,
            rsi_value=62.0,
            macd_data={"macd_line": 1.0, "signal_line": 0.5, "histogram": 0.5},
            change_percent=6.0,
            volume_data={"latest_volume": 300, "avg_volume_20d": 200, "ratio": 1.5},
        )
        assert result["technical_score"] == 100
        assert len(result["score_breakdown"]) == 5

    def test_weak_downtrend_scores_low(self):
        result = scoring.compute_technical_score(
            price=90.0,
            sma_20=100.0,
            sma_50=105.0,
            rsi_value=35.0,
            macd_data={"macd_line": -1.0, "signal_line": -0.5, "histogram": -0.5},
            change_percent=-8.0,
            volume_data={"latest_volume": 50, "avg_volume_20d": 200, "ratio": 0.25},
        )
        assert result["technical_score"] < 30

    def test_missing_data_scores_neutral(self):
        result = scoring.compute_technical_score(
            price=100.0,
            sma_20=None,
            sma_50=None,
            rsi_value=None,
            macd_data=None,
            change_percent=None,
            volume_data=None,
        )
        # Every component falls back to its neutral (10-point) score.
        assert result["technical_score"] == 50

    def test_score_never_exceeds_100(self):
        result = scoring.compute_technical_score(
            price=200.0,
            sma_20=100.0,
            sma_50=90.0,
            rsi_value=55.0,
            macd_data={"macd_line": 5.0, "signal_line": 1.0, "histogram": 4.0},
            change_percent=20.0,
            volume_data={"latest_volume": 1000, "avg_volume_20d": 100, "ratio": 10.0},
        )
        assert result["technical_score"] <= 100


class TestRiskEngine:
    def test_low_risk_profile(self):
        result = risk.assess_stock_risk(
            volatility_20d_percent=1.0, rsi_14=55, price_change_10d_percent=2.0, technical_score=80
        )
        assert result["risk_level"] == "LOW"
        assert result["risk_score"] == 0

    def test_high_risk_profile(self):
        result = risk.assess_stock_risk(
            volatility_20d_percent=4.5, rsi_14=78, price_change_10d_percent=15, technical_score=30
        )
        assert result["risk_level"] == "HIGH"
        assert result["risk_score"] == 100

    def test_medium_risk_profile(self):
        result = risk.assess_stock_risk(
            volatility_20d_percent=2.5, rsi_14=45, price_change_10d_percent=1, technical_score=62
        )
        assert result["risk_level"] == "LOW"  # only moderate volatility flagged = 20 pts

    def test_no_reasons_gives_default_message(self):
        result = risk.assess_stock_risk(
            volatility_20d_percent=0.5, rsi_14=50, price_change_10d_percent=0, technical_score=90
        )
        assert result["risk_level"] == "LOW"
        assert "No significant" in result["reasons"][0]


class TestPortfolioRisk:
    def test_no_allocation_is_unavailable(self):
        from app.services.portfolio_service import _assess_portfolio_risk

        result = _assess_portfolio_risk([], 0)
        assert result["risk_level"] == "unavailable"

    def test_concentrated_portfolio_is_high_risk(self):
        from app.services.portfolio_service import _assess_portfolio_risk

        result = _assess_portfolio_risk([{"symbol": "TCS", "percent": 60.0}, {"symbol": "SBIN", "percent": 40.0}], 2)
        assert result["risk_level"] == "HIGH"

    def test_diversified_portfolio_is_low_risk(self):
        from app.services.portfolio_service import _assess_portfolio_risk

        allocation = [{"symbol": s, "percent": 25.0} for s in ["TCS", "SBIN", "INFY", "HDFCBANK"]]
        result = _assess_portfolio_risk(allocation, 4)
        assert result["risk_level"] == "LOW"

    def test_single_holding_bumped_to_at_least_medium(self):
        from app.services.portfolio_service import _assess_portfolio_risk

        result = _assess_portfolio_risk([{"symbol": "TCS", "percent": 20.0}], 1)
        assert result["risk_level"] in ("MEDIUM", "HIGH")


class TestDecisionMatrix:
    def test_high_score_low_risk_is_favorable(self):
        result = decision.compute_decision(80, "LOW")
        assert result["decision"] == "FAVORABLE"
        assert "not financial advice" in result["disclaimer"].lower()

    def test_low_score_high_risk_is_high_risk_label(self):
        result = decision.compute_decision(30, "HIGH")
        assert result["decision"] == "HIGH RISK"

    def test_mid_score_medium_risk_is_monitor(self):
        result = decision.compute_decision(60, "MEDIUM")
        assert result["decision"] == "MONITOR"

    def test_disclaimer_always_present(self):
        for score in (10, 55, 95):
            for level in ("LOW", "MEDIUM", "HIGH"):
                result = decision.compute_decision(score, level)
                assert "disclaimer" in result
                assert len(result["disclaimer"]) > 0
