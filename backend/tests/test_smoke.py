"""
Smoke Tests — Automated verification of all critical endpoints.
Uses TestClient for in-process testing (no live server required).

Run: cd backend && python -m pytest tests/test_smoke.py -v
"""


def test_liveness(client):
    resp = client.get("/api/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"


def test_readiness(client):
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "healthy"


def test_system_status(client):
    resp = client.get("/api/health/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "operational"
    assert "uptime_hours" in body


def test_dashboard_page(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_trading_hub_page(client):
    resp = client.get("/trading-hub")
    assert resp.status_code == 200


def test_trading_tools_page(client):
    resp = client.get("/trading-tools")
    assert resp.status_code == 200


def test_external_factors_page(client):
    resp = client.get("/external-factors")
    assert resp.status_code == 200


def test_landing_page(client):
    resp = client.get("/landing")
    assert resp.status_code == 200


def test_pricing_page(client):
    resp = client.get("/pricing")
    assert resp.status_code == 200


def test_market_overview(client):
    resp = client.get("/api/trading/market-overview")
    assert resp.status_code == 200
    body = resp.json()
    stocks = [s for s in body.get("top_stocks", []) if s.get("price", 0) > 0]
    assert len(stocks) > 0


def test_top_movers(client):
    resp = client.get("/api/trading/top-movers")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body.get("gainers", [])) > 0


def test_sectors(client):
    resp = client.get("/api/trading/sectors")
    assert resp.status_code == 200
    body = resp.json()
    sectors = [s for s in body.get("sectors", []) if s.get("price", 0) > 0]
    assert len(sectors) > 0


def test_etfs(client):
    resp = client.get("/api/trading/etf-overview")
    assert resp.status_code == 200
    body = resp.json()
    etfs = [e for e in body.get("etfs", []) if e.get("price", 0) > 0]
    assert len(etfs) > 0


def test_technical_analysis(client):
    resp = client.get("/api/trading/technical-analysis/NVDA")
    assert resp.status_code == 200
    body = resp.json()
    assert "signal" in body
    assert "technicals" in body


def test_options_data(client):
    resp = client.get("/api/trading/options/NVDA")
    assert resp.status_code == 200
    body = resp.json()
    assert "options_chain" in body


def test_stock_search(client):
    resp = client.get("/api/trading/search?q=NVIDIA")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] > 0


def test_backtest_strategies(client):
    resp = client.get("/api/backtest/strategies")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["strategies"]) == 4


def test_backtest_run(auth_client):
    resp = auth_client.post(
        "/api/backtest/run",
        json={"symbol": "SPY", "strategy": "sma_crossover", "days": 180, "initial_capital": 10000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "metrics" in body
    assert "equity_curve" in body


def test_earnings_upcoming(client):
    resp = client.get("/api/earnings/upcoming?days=90")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total"] > 0


def test_alerts_list(client):
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert "alerts" in body


def test_alerts_check(client):
    resp = client.get("/api/alerts/check")
    assert resp.status_code == 200
    body = resp.json()
    assert "checked" in body


def test_debug_endpoints_disabled(client):
    resp = client.get("/docs")
    assert resp.status_code == 404


def test_error_responses_sanitized(client):
    resp = client.get("/api/trading/stocks/INVALIDSTOCK")
    assert resp.status_code == 404
    body = resp.text.lower()
    assert "traceback" not in body
    assert "File" not in resp.text
